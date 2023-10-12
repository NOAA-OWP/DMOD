# Git Strategy

- [Branching Design](#branching-design)
- [Contributing](#contributing)
    - [TL;DR](#contributing-tldr)
    - [Getting Started With Your Fork](#getting-started-with-your-fork)
    - [Fork Consistency Requirements](#fork-consistency-requirements)
    - [Fork Setup Suggestions](#fork-setup-suggestions)
- [Keeping Forks Up to Date](#keeping-forks-up-to-date)
    - [Getting Upstream Changes](#getting-upstream-changes)
    - [Rebasing Development Branches](#rebasing-development-branches)
    - [Fixing Diverging Development Branches](#fixing-diverging-development-branches)

## Branching Design

- The main DMOD repo has a primary long-term branch called **master**
    - There may be other branches for specific purposes, but these should still derive from `master`
- Interaction with DMOD repo is done via pull requests (PRs) to this `master` branch

## Contributing

- [TL;DR](#contributing-tldr)
- [Getting Started With Your Fork](#getting-started-with-your-fork)
- [Fork Consistency Requirements](#fork-consistency-requirements)
- [Fork Setup Suggestions](#fork-setup-suggestions)

### Contributing TL;DR

To work with the repo and contribute changes, the basic process is as follows:

- Create your own DMOD fork in Github
- Clone your fork and [setup your repo on your local development machine](#getting-started-with-your-fork)
- Make sure to [keep your fork and your local clone(s) up to date](#keeping-forks-up-to-date) with the upstream DMOD repo, [ensuring histories remain consistent](#fork-consistency-requirements) by performing [rebasing](#rebasing-development-branches)
- Figure out a branching strategy that works for you, with [this strategy offered as a suggestion](#fork-setup-suggestions)
- Make changes you want to contribute, commit them locally, and push them to your Github fork
- Submit pull requests to the upstream repo's `master` from a branch in your fork when you have a collection of changes ready to be incorporated

### Getting Started With Your Fork

After creating a fork in Github, clone a local development repo from the fork.  This should make the fork a remote for that local repo, typically named **origin**.  

Add the main DMOD repo as a second remote for the local clone. The standard convention, used here and elsewhere, is to name that remote `upstream`.  Doing the addition will look something like:

    # Add the remote 
    git remote add upstream https://github.com/NOAA-OWP/DMOD.git
        
    # Verify
    git remote -v

Set up a local user and email in the local repo's configuration.  
    
    cd local_repo_directory
    git config user.name "John Doe"
    git config user.email "john@doe.org"
    
Alternatively, one could also set these in the machine's global Git config (or rely upon the global settings if already configured).

     git config --global user.name "John Doe"
     git config --global user.email "john@doe.org"
     
### Fork Consistency Requirements

Within a local repo and personal fork, users are mostly free to do whatever branching strategy works for them.  However, a branch used for a pull request typically should be (re)based on the `HEAD` commit of the current OWP `upstream/master` branch, to ensure the repo history remains consistent.

### Fork Setup Suggestions

Note that while this setup is not strictly required, examples and instructions in this document may assume its use.
    
Maintain a personal `master` branch, on any local development clones and within a personal fork, just as [a place to rebase changes from `upstream/master`](#getting-upstream-changes).  Do not do any development work or add any commits to these directly.  Just keep these as a "clean," current copy of the `upstream/master` branch.  

Use separate feature branches for development work as appropriate.  When preparing to make a PR, making sure the branch is both up to date with `upstream/master` and has all the desired local changes.

A separate, "clean" local `master` should be easy to keep it in sync with `upstream/master`, which in turn will make it relatively easy to rebase local development branches on `master` whenever needed.  This simplifies maintaining the base-commit consistency requirement for the branches used for pull requests.

Clean up above mentioned PR branches regularly (i.e., once their changes get incorporated).  This is generally a good practice for other local or fork development branches, to avoid having [diverged histories that need to be fixed](#fixing-diverging-development-branches).

## Keeping Forks Up to Date

- [A Rebase Strategy](#a-rebase-strategy)
- [Getting Upstream Changes](#getting-upstream-changes)
- [Rebasing Development Branches](#rebasing-development-branches)
- [Fixing Diverging Development Branches](#fixing-diverging-development-branches)


To remain consistent with changes to the official OWP DMOD repo (i.e., the **upstream** repo), a developer will need to regularly synchronize with it.  This requires having an `upstream` remote configured, as described in the section on [getting started with your fork and local repo](#getting-started-with-your-fork).  

### A Rebase Strategy

The development team for DMOD uses a *rebase* strategy for integrating code changes, rather than a *merge* strategy.  More information on rebasing is [available here](https://git-scm.com/book/en/v2/Git-Branching-Rebasing), but the main takeaway is that it is important all changes are integrated into branches using this approach.  Deviation from this will likely cause a bit of mess with branch commit histories, which could force rejection of otherwise-good PRs.


### Getting Upstream Changes

When it is time to check for or apply updates to a personal fork and/or a local repo, check out the local `master` branch and do fetch-and-rebase, which can be done with `pull` and the `--rebase` option:

    # Checkout local master branch 
    git checkout master
    
    # Fetch and rebase changes
    git pull --rebase upstream master
    
Then, make sure these get pushed to the personal fork. Assuming a typical setup where a developer has cloned from a fork, and still has `master` checked out, that is just:

    # Note the assumptions mentioned above that are required for this syntax
    git push

Depending on individual setup, a developer may want to do this immediately (e.g., if the `master` branch is "clean", as [discussed in the forking suggestions](#fork-setup-suggestions)), or wait until the local `master` is in a state ready to push to the personal fork. 

### Rebasing Development Branches    
    
When the steps in [Getting Upstream Changes](#getting-upstream-changes) do bring in new commits that update `master`, rebase any local development branches were previously created. E.g., 

    # If using a development branch named 'dev'
    git checkout dev
    git rebase master

See documentation on [the "git rebase" command](https://git-scm.com/docs/git-rebase) for more details.
    
#### Interactive Rebasing

It is possible to have more control over rebasing by doing an interactive rebase.  E.g.:

    git rebase -i master

This will open up a text editor allowing for reordering, squashing, dropping, etc., development branch commits prior to rebasing them onto the new base commit from `master`.  See the [**Interactive Mode**](https://git-scm.com/docs/git-rebase#_interactive_mode) section on the rebase command  for more details.
    
### Fixing Diverging Development Branches

If a local development branch is already pushed to a remote fork, and then later rebasing the local branch is necessary, doing so will cause the histories to diverge.  For simple cases, the fix is to just force-push the rebased local branch.

    # To force-push to fix a divergent branch
    git push -f origin dev
    
However, extra care is needed if multiple developers may be using the branch in the fork (e.g., a developer is collaborating with someone else on a large set of changes for some new feature).  The particular considerations and best ways to go about things in such cases are outside the scope of this document.  Consult Git's documentation and Google, or contact another contributor for advice.

     