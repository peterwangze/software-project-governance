# Install Software Project Governance in zcode

Add this repository as a marketplace in zcode, then install the plugin by its registered name.

```text
/plugin marketplace add peterwangze/software-project-governance
/plugin install software-project-governance@spg
```

For a local checkout, give `/plugin marketplace add` the path to the directory containing `.claude-plugin/marketplace.json`. The registry uses `source: "./"`, so the install resolves the plugin from that directory. If starting from an offline archive, extract it first. Support for importing a zip directly depends on the host.

Restart the host if required. Check `/plugins list` for `software-project-governance`, then run `/governance` in the target project. This checks the installation on that host. Official listing and wider runtime support require independent evidence. [Submission review](../requirements/official-submission-final-bundle-review-0.49.0.md#carry-forward-blockers)

## Migrate a seed-based installation from 0.56–0.61

Before upgrading, run `python project/zcode-local-load.py --unload` from the old 0.61.x checkout to remove this plugin’s seed entry. Then install from the marketplace as above. The old loader can be recovered from the [0.61.0 release](https://github.com/peterwangze/software-project-governance/blob/v0.61.0/project/zcode-local-load.py).
