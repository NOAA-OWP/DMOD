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

- Main **upstream** repo has only the single long-term branch called **master**; i.e., `upstream/master` 
    - There may occasionally be other temporary branches for specific purposes
- Interaction with **upstream** repo is done exclusively via pull requests (PRs) to `upstream/master`

## Contributing

- [TL;DR](#contributing-tldr)
- [Getting Started With Your Fork](#getting-started-with-your-fork)
- [Fork Consistency Requirements](#fork-consistency-requirements)
- [Fork Setup Suggestions](#fork-setup-suggestions)

### Contributing TL;DR

To work with the repo and contribute changes, the basic process is as follows:

- Create your own fork in Github of the main **upstream** repository
- Clone your fork and [setup your repo on your local development machine](#getting-started-with-your-fork)
- Make sure to [keep your fork and your local clone(s) up to date](#keeping-forks-up-to-date) with the main upstream repo, [ensuring histories remain consistent](#fork-consistency-requirements) by performing [rebasing](#rebasing-development-branches)
- Figure out a branching strategy that works for you, with [this strategy offered as a suggestion](#fork-setup-suggestions)
- Make changes you want to contribute, commit them locally, and push them to your Github fork
- Submit pull requests to `upstream/master` from a branch in your fork when you have a collection of changes ready to be incorporated

### Getting Started With Your Fork

After creating your fork in Github, clone your local repo from the fork.  This should make your fork a remote for you local repo, typically named **origin**.  

Add the main **upstream** repo as a second remote in your local clone. The standard convention, used here and elsewhere, is to name that remote `upstream`.  Doing the addition will look something like:

    # Add the remote 
    git remote add upstream https://github.com/NOAA-OWP/DMOD.git
        
    # Verify
    git remote -v

Set up your user name and email in your local repo's configuration, unless you are confident that you have values set as needed in your global Git config.  
    
    cd local_repo_directory
    git config user.name "John Doe"
    git config user.email "john@doe.org"
    
Potentially, you could also set this in your machine's global Git config (or rely upon the global settings if you have already configured them).

     git config --global user.name "John Doe"
     git config --global user.email "john@doe.org"
     
### Fork Consistency Requirements

Within your own local repo and personal fork, you are mostly free to do whatever branching strategy works for you.  However, branches used for PRs must have all new commits based on the current `HEAD` commit of the `upstream/master` branch, to ensure the repo history remains consistent.  I.e., you need to make sure you rebase the branch with your changes before making a PR.  How you go about this is up to you, but the following suggested setup will make that relatively easy.

### Fork Setup Suggestions

Note that while this setup is not strictly required, examples and instructions in this document may assume its use.
    
Have your own `master` branch, on your local clone and within your personal fork, just as [a place to rebase changes from `upstream/master`](#getting-upstream-changes).  Do not do any development work or add any of your own changes directly.  Just keep it as a "clean," current copy of the `upstream/master` branch.  

Use separate branches for development work as you see fit.  When preparing to make a PR, create a new branch just for that PR, making sure it is both up to date with **upstream** and has all the desired local changes.  Wait to actually push it to your fork until that has been done and your are ready create the PR.

A separate, "clean" local `master` should be easy to keep it in sync with `upstream/master`, which in turn will make it relatively easy to rebase local development branches whenever needed.  This simplifies maintaining the base-commit consistency requirement for the branches you will use for pull requests.

Clean up above mentioned PR branches regularly (i.e., once their changes get incorporated).  You may also want to do this for the other development branches in your fork, or else you'll end up with branches having [diverged histories that need to be fixed](#fixing-diverging-development-branches).

## Keeping Forks Up to Date

- [Getting Upstream Changes](#getting-upstream-changes)
- [Rebasing Development Branches](#rebasing-development-branches)
- [Fixing Diverging Development Branches](#fixing-diverging-development-branches)


Note that to stay in sync with other separate changes added to the main **upstream** repo, you will typically need to regularly synchronize with it.  This requires having an `upstream` remote configured, as described in the section on [getting started with your fork and local repo](#getting-started-with-your-fork).  

### Getting Upstream Changes

When you want to check for or apply updates to your fork (and your local repo), locally check out your `master` branch and do fetch-and-rebase, which can be done with `pull` and the `--rebase` option:

    # Checkout local master branch 
    git checkout master
    
    # Fetch and rebase changes
    git pull --rebase upstream master
    
Then, make sure these get pushed to your fork. Assuming a typical setup where you have cloned from your fork, and you still have `master` checked out, that is just:

    # Note the assumptions mentioned above that required for this syntax
    git push

Depending on your individual setup, you may want to do this immediately (e.g., if your `master` branch is "clean", as [discussed in the forking suggestions](#fork-setup-suggestions)), or wait until your local `master` is in a state ready to push to your fork. 

### Rebasing Development Branches    
    
When the steps in [Getting Upstream Changes](#getting-upstream-changes) do bring in new commits that update `master`, you should rebase any local branches local development branches you had previously created. E.g., 

    # If using a development branch named 'dev'
    git checkout dev
    git rebase master
    
Alternatively, you can do an interactive rebase.  This will open up a text editor allowing you to rearrange, squash, omit, etc. your commits when you rebase your development branch onto the new state of `master`. 

    git rebase -i master
    
### Fixing Diverging Development Branches

If you have already pushed a local development branch to your fork, and then later need to rebase the branch, doing so will cause the history to diverge.  If you are the only one using your fork, this is easy to fix by simply force-pushing your rebased local branch.

    # To force-push to fix a divergent branch
    git push -f origin dev
    
However, you will need to be careful with this if you are not the only one using you fork (e.g., you are collaborating with someone else on a large set of changes for some new feature).  The particular considerations and best ways to go about things in such cases are outside the scope of this document.  Consult Git's documentation and Google, or contact another contributor for advice.

     