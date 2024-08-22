# Locally Customizing the ngen Worker

It simply isn't possible to bundle every possible ngen-compatible BMI module into the job worker image Dockerfile.  As such, the source Dockerfile doesn't try to include everything and only integrates a small number of OWP-developed BMI modules.  

But, it is possible to use other BMI modules outside this small subset in the DMOD job worker images.

Several special files can be added to this directory in a local copy of the repo that will enable customization of the built job worker Docker images.  The regular image building process for DMOD is designed to use these files, when present, to incorporate customizations into the worker images.  One or more may be used in combination, or none can be used and the "stock" image will be built.

These special files are configured to be ignored by Git, keeping them from being committed to the repo and allowing them to be unique to each situation.

In summary, it is possible to:
- provide a `requirements.txt` file to customize what Python packages are installed
- list external Git repositories to clone and build via a file, though this will only work in situations meeting some specific criteria
- provide a specialized script to manually perform more advanced or nuanced customization

## Supply `requirements.txt` File

If a `requirements.txt` file is present within this directory, it will be used by an additional call to `pip` during the image build process, installing the Python packages listed within the file.  This is likely the easiest way to incorporate more Python BMI modules, as long as they are publicly accessible.  

Keep in mind that, even if ready-made packages are not available via something like PyPI, `pip` supports [installing directly from version control systems](https://pip.pypa.io/en/stable/topics/vcs-support/) like Git.

## List of Repos Built By Helper Script

Users can locally create a file named `cmake_repositories.txt` in this directory and add a list of Git URLs for repos supporting building with CMake.

If a `cmake_repositories.txt` file is added in this directory, each line will be treated as Git URL and run through the `clone_and_cmake_build.sh` helper script.  Though it can only handle very simple use cases, this script will automatically clone the repo, build shared libraries and other artifacts, and put these things into appropriate places in the built image.  While limited, it may be useful for things like C or C++ BMI modules.

For this to work for a provided Git repo, a few conditions must hold true:

- the Git repository must be accessible at the given URL anonymously
- the script doesn't provide a branch, so whatever the default branch is (e.g., `master` or `main`) must be suitable
- the contents of the repo must be set up to build with **CMake**
- no extra, deliberate configuration of **CMake** variables should be necessary 
  - (except `CMAKE_BUILD_TYPE` and `CMAKE_INSTALL_PREFIX`, which are pre-set in the script)
- running `cmake --build <build_dir>` will build anything/everything required
  - i.e., it must not be necessary to build a specific **CMake** `target`

## Use Manual Customization Script 

If the above methods are insufficient, it is possible to write a more bespoke script for configuring whatever customization is needed within the image, while also avoiding commiting this script directly to the repo.  This allows for finer-grained control but also puts more responsibility on the user.  To do this:

1. Create a script named `customize.sh` within this directory
2. Have the script do whatever cloning, configuring, building, etc. tasks are necessary
3. Make sure built artifacts (libraries, executables, static data/config files) are placed within `/dmod/` subdirectories within the image build so that `ngen` can find them
   1. `/dmod/bin/` for executables
   2. `/dmod/bmi_module_data/` for static module data and configs
   3. `/dmod/shared_libs/` for compiled shared libraries
   4. Note that there is also a Python virtual environment at `/dmod/venv/`, though this should be active in the environment when the script is run; i.e., installing packages using `pip` should get things there without any extra steps