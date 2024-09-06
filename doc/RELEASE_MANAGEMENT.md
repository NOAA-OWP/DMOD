# Release Management

The page discusses the release process for official versions of DMOD.  This process is very much interrelated to the repo  branching management model, as discussed in detail on the [GIT_USAGE](./GIT_USAGE.md) doc.

# The Release Process

## TL;DR

The release process for DMOD can be summarized fairly simply:
- A version name is finalized
- A release branch is created
- Testing, QA, fixes are done on the release branch
- Once ready the release is tagged and changes are pulled into `production` and `master`

## Process Steps


[comment]: <> (TODO: Document release manual testing and QA procedures)

1. The next DMOD version name/number is [decided/finalized](#rules-for-version-numbers)
2. A release branch, based on `master`, is created in the official OWP repo
    - The name of this branch will be `release-X` for version `X`
3. All necessary testing and quality pre-release tasks are performed using this release branch
    - **TODO**: to be documented in more detail
4. (If necessary) Bug fixes, documentation updates, and other acceptable, non-feature changes are applied to the release branch
   - Such changes should go through some peer review process before inclusion in the official OWP branch (e.g., PRs, out-of-band code reviews, etc.)
   - **TODO**: process to be decided upon and documented
5. Steps 3. and 4. are repeated as needed until testing, quality checks, etc. in Step 3. do not require another iteration of Step 4.
    - At this point, the branch is ready for official release
6. All changes in the release branch are incorporated into `production` in the official OWP repo
    - Note that **rebasing** should be used to reconcile changes ([see here](GIT_USAGE.md#a-rebase-strategy) for more info)
7. The subsequent `HEAD` commit of `production` is tagged with the new version in the official OWP repo
8. All changes in the release branch are incorporated back into `master` in the official OWP repo
   - This will include things like bug fixes committed to `release-X` after it was branched from `master`
   - As with `production` in Step 6., this should be [done using rebasing](GIT_USAGE.md#a-rebase-strategy)
9. The release branch is deleted from the OWP repo (and, ideally, other clones and forks)
10. (If necessary) Any additional tags are applied as needed to the `HEAD` commit of `production` in the official OWP repo
    - At this time none are currently needed, but there are plans to consider these in the future for things like specific package versions of contained packages

# Versions

The versioning for DMOD is a little complicated.  

DMOD contains the sources of several independently-versioned Python packages; e.g., `dmod-core-0.19.0`.  As long as this code remains organized as multiple separate packages, the package versions need to continue to be maintained individually.  

DMOD contains other source code wholly separate from these package, such as helper scripts, Dockerfiles, stack configurations, and other files.  These are not contained in some inner organizational unit with its own versioning, and many (if not all) of them are particularly relevant to DMOD deployment.  

As such, DMOD utilizes another, independent versioning scheme for itself as a whole.

## Rules for Version Numbers

Version numbers for DMOD should follow a system akin to [Semantic Versioning](https://semver.org/), using the typical `MAJOR.MINOR.PATCH` pattern.  Because of DMOD's design and purpose, the rules for incrementing components need to be applied at slightly higher levels:

1. `MAJOR` increments if incompatible changes are made with respect to job execution, data orchestration, infrastructure capabilities, or the deployment process; examples include (but are not limited to)
   * any executable job types are removed
   * previously satisfactory data formats to fulfill a job requirement become no longer satisfactory
   * a special process is needed to upgrade an existing deployment that goes significantly beyond repeating steps performed when setting up a new deployment
2. `MINOR` increments if significant, backwards compatible changes are made with respect to job execution, data orchestration, infrastructure capabilities, or the deployment process
   * a new executable job type is added
   * an additional dataset format is added
   * a new DMOD service is added
   * new iterations of service or worker runtime entities (e.g., Docker images) must be generated, but using the same processes and tools used previously
3. `PATCH` increments if only smaller or less noticeable changes than those above are made
