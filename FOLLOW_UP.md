# Follow-Up Tasks

After completing the repository reorganization, the following issues require immediate attention:

## 1. Git LFS Setup for Large Files

During push, GitHub reported:
> File src/models/handwriting_model/checkpoints/mock_model.pt is 68.52 MB; this is larger than GitHub's recommended maximum file size of 50.00 MB

### Tasks:

- [ ] Install Git LFS client on development machines
  ```bash
  # Debian/Ubuntu
  apt-get install git-lfs
  
  # macOS
  brew install git-lfs
  ```

- [ ] Initialize Git LFS in the repository
  ```bash
  git lfs install
  ```

- [ ] Track large model files with Git LFS
  ```bash
  git lfs track "*.pt"
  git lfs track "*.pth"
  git lfs track "*.onnx"
  git lfs track "*.pb"
  ```

- [ ] Add the `.gitattributes` file
  ```bash
  git add .gitattributes
  ```

- [ ] Re-add the large files
  ```bash
  git add src/models/handwriting_model/checkpoints/mock_model.pt
  git commit -m "chore: move large model files to Git LFS"
  ```

- [ ] Update the README.md with Git LFS requirements
  ```md
  ## Large File Storage
  
  This repository uses Git LFS for large files like model checkpoints.
  Please ensure Git LFS is installed before cloning:
  
  ```bash
  git lfs install
  git clone --recursive https://github.com/remarkable-ink-link/inklink.git
  ```
  ```

## 2. Security Vulnerabilities

GitHub reported:
> GitHub found 2 vulnerabilities on rmulligan/remarkable-ink-link's default branch (1 critical, 1 moderate)

### Tasks:

- [ ] Review GitHub Security tab and Dependabot alerts
  - Navigate to: https://github.com/rmulligan/remarkable-ink-link/security/dependabot

- [ ] Address critical vulnerability first
  - [ ] Identify the vulnerable dependency
  - [ ] Test compatibility with updated version
  - [ ] Update the dependency in requirements or package.json

- [ ] Address moderate vulnerability 
  - [ ] Evaluate impact and urgency
  - [ ] Update if no breaking changes are expected

- [ ] Run test suite after dependency updates
  ```bash
  poetry run pytest
  ```

- [ ] Create a dedicated security update PR
  - Use title: "security: address critical and moderate vulnerabilities"
  - Reference Dependabot alerts in PR description

## 3. Future File Size Management

To prevent similar issues in the future:

- [ ] Add file size checking to pre-commit hooks
- [ ] Create a script to identify large files before commit
- [ ] Consider a more robust model weight management strategy:
  - Separate model repository with releases
  - Model downloading script at first run
  - Hosted model weights with versioning

