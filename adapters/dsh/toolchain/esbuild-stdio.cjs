/** Process-local transport for the pinned Windows Vite/esbuild toolchain. */
'use strict'

const subprocess = require('node:child_process')
const crypto = require('node:crypto')
const fs = require('node:fs')
const net = require('node:net')
const { EventEmitter } = require('node:events')
const { syncBuiltinESMExports } = require('node:module')
const { basename, isAbsolute, join, relative, sep } = require('node:path')
const { PassThrough } = require('node:stream')
const { pathToFileURL } = require('node:url')

const ESBUILD_SHA256 = 'b868c8d988ffe76006c03c91f856312c312e42e2f3932a6bb56d7f4a1790c8b3'
const VITE_CHUNK_SHA256 = 'bfa94186daff535fefdf286088c1588fad6b02c01ef11cd3b42a6cb3e4c90767'
const nativeSpawn = subprocess.spawn
const nativeExec = subprocess.exec

function inside(root, path) {
  const rest = relative(root, path)
  return !isAbsolute(rest) && rest !== '..' && !rest.startsWith('..' + sep)
}

function digest(path) { return crypto.createHash('sha256').update(fs.readFileSync(path)).digest('hex') }

function settings() {
  const values = ['SPG_WORKSPACE_NPM_WORKSPACE', 'SPG_WORKSPACE_NPM_ROOT', 'SPG_WORKSPACE_NPM_PYTHON']
    .map(key => process.env[key])
  if (process.platform !== 'win32' || !process.argv[1]
      || values.some(value => !value || !isAbsolute(value))) return null
  try {
    const [workspace, root, python] = values.map(value => fs.realpathSync(value))
    if (!inside(workspace, root) || inside(workspace, python) || basename(python).toLowerCase() !== 'python.exe'
        || !fs.statSync(python).isFile()
        || relative(root, fs.realpathSync(process.cwd()))) return null
    const cli = relative(root, fs.realpathSync(process.argv[1])).split(sep).join('/').toLowerCase()
    if (!['node_modules/vite/bin/vite.js', 'node_modules/vitest/vitest.mjs'].includes(cli)) return null
    const exe = fs.realpathSync(join(root, 'node_modules', '@esbuild', 'win32-x64', 'esbuild.exe'))
    const viteChunk = fs.realpathSync(join(root, 'node_modules', 'vite', 'dist', 'node', 'chunks', 'dep-BK3b2jBa.js'))
    if (!inside(root, exe) || !inside(root, viteChunk)
        || digest(exe) !== ESBUILD_SHA256 || digest(viteChunk) !== VITE_CHUNK_SHA256) return null
    return { root, python, exe, viteChunk: pathToFileURL(viteChunk).href }
  } catch {
    return null
  }
}

function relay(config) {
  const handle = new EventEmitter()
  const nonce = crypto.randomBytes(32).toString('hex')
  const expected = Buffer.from(nonce, 'ascii')
  handle.stdin = new PassThrough()
  handle.stdout = new PassThrough()
  let child, channel, stopped = false, referenced = true
  const pending = new Set()
  const server = net.createServer({ allowHalfOpen: true }, authenticate)
  const timer = setTimeout(() => finish(new Error('native esbuild relay startup timed out')), 8_000)

  function authenticate(socket) {
    if (pending.size >= 4 || channel) return socket.destroy()
    pending.add(socket)
    socket.on('close', () => pending.delete(socket))
    socket.on('error', () => {
      if (socket === channel) finish(new Error('native esbuild relay connection failed'))
    })
    let offset = 0
    function consume(chunk) {
      const size = Math.min(chunk.length, expected.length - offset)
      if (!crypto.timingSafeEqual(chunk.subarray(0, size), expected.subarray(offset, offset + size))) {
        return socket.destroy()
      }
      offset += size
      if (offset !== expected.length) return
      if (channel) return socket.destroy()
      channel = socket
      socket.removeListener('data', consume)
      for (const other of pending) if (other !== socket) other.destroy()
      server.close()
      clearTimeout(timer)
      if (chunk.length > size) handle.stdout.write(chunk.subarray(size))
      handle.stdin.pipe(socket)
      socket.pipe(handle.stdout)
      syncRef()
    }
    socket.on('data', consume)
  }

  function syncRef() {
    for (const item of [timer, server, child, channel]) item?.[referenced ? 'ref' : 'unref']?.()
  }

  function finish(error) {
    if (stopped) return false
    stopped = true
    clearTimeout(timer)
    server.close()
    for (const socket of pending) socket.destroy()
    if (!channel && child?.exitCode === null) child.kill()
    if (error) handle.emit('error', error)
    handle.stdout.end()
    return true
  }

  handle.ref = () => { referenced = true; syncRef() }
  handle.unref = () => { referenced = false; syncRef() }
  handle.kill = () => finish()
  server.on('error', finish)
  server.listen({ host: '127.0.0.1', port: 0, exclusive: true }, () => {
    if (stopped) return
    try {
      child = nativeSpawn(config.python, ['-E', '-s', join(__dirname, 'esbuild-relay.py'), config.exe,
        String(server.address().port)], {
        cwd: config.root, shell: false, stdio: ['ignore', 'ignore', 'inherit'], windowsHide: true,
        env: { ...process.env, SPG_WORKSPACE_NPM_TOKEN: nonce },
      })
      child.on('error', finish)
      child.on('exit', status => {
        if (status !== 0 || !channel) finish(new Error('native esbuild relay stopped unexpectedly'))
      })
      syncRef()
    } catch (error) { finish(error) }
  })
  return handle
}

const config = settings()
if (config) {
  subprocess.spawn = function spawn(command, args, options) {
    try { return nativeSpawn.apply(this, arguments) }
    catch (error) {
      if (error.code !== 'EPERM' || typeof command !== 'string' || relative(config.exe, command)
          || typeof options?.cwd !== 'string' || relative(config.root, options.cwd)
          || args?.length !== 2 || args[0] !== '--service=0.21.5' || args[1] !== '--ping'
          || JSON.stringify(options?.stdio) !== '["pipe","pipe","inherit"]') throw error
      process.stderr.write('[dsh-workspace-npm] using native esbuild 0.21.5 stdio relay\n')
      return relay(config)
    }
  }
  subprocess.exec = function exec(command, callback) {
    try { return nativeExec.apply(this, arguments) }
    catch (error) {
      // Vite already uses ordinary realpath when this optional probe fails asynchronously.
      if (error.code !== 'EPERM' || command !== 'net use' || typeof callback !== 'function'
          || !error.stack?.includes(`optimizeSafeRealPathSync (${config.viteChunk}:`)) throw error
      process.nextTick(callback, error, '', '')
    }
  }
  syncBuiltinESMExports()
}
