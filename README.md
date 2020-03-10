# README

This repository contains modules required to run the Colorado Habitat Exchange HQT.

Copyright 2017-2020 Environmental Incentives, LLC.

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this code except in compliance with the License. You may obtain a copy of the License at

  https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

## Collaborating

To contribute to these scripts, fork this repo and clone it within a folder named `Scripts`, located in the root of a copy of the correct state's HQT Data Package.

```bash
git clone <url> Scripts
```

It's generally acceptable to work on the master branch for this project. See [this resource](https://eanderson-ei.github.io/ei-dev/git/collaborating-with-git/) for more information on submitting pull requests.

Make sure any files or folders created by your IDE are included in the `.gitignore` file before your first commit (e.g., `.vscode/`, `.idea/`).

Please update the `CHANGELOG.md` file with release notes following the practices documented [here](https://keepachangelog.com/en/1.0.0/). Include changes to the Data Package as well, as those changes must be replicated locally.

If you are changing code for one state, consider whether it is relevant to other states' codebase and make the changes there as well.

## Distribution

When packaging the Data Package for distribution following a new release or bug fix, the `.git`, `.gitignore`, `README.md`, `CHANGELOG.md` and `LICENSE` files may all be preserved. Consider deleting `.pyc` files and `__pycache__` folders and anything created by your IDE.

Make sure the `CHANGELOG.md` file is up to date, and clean it up if needed.

Importantly, do not confuse this version with the *official* version of the HQT! The official version is the version that was distributed by the program's administrator and is available on the program's website. If you are providing technical assistance or verifying a project assessment, make sure to use the appropriate version. Zipped copies of each official distribution are maintained on Sharepoint.

 