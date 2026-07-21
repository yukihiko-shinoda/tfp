#!/usr/bin/env bash
TENV_VERSION=${1:-"v4.14.8"}
BUILDARCH=$(dpkg --print-architecture)

apt upgrade
apt update
# Git required when download some aws module:
#   Could not download module "s3_bucket"
#   (services/performance_reposync/cloudwatchlogs.tf:11) source code from
#   "git::https://github.com/terraform-aws-modules/terraform-aws-s3-bucket?ref=v1.22.0":
#   error downloading
#   'https://github.com/terraform-aws-modules/terraform-aws-s3-bucket?ref=v1.22.0':
#   git must be available and on the PATH.
# see:
#   - Module Sources - Terraform by HashiCorp
#     https://www.terraform.io/docs/language/modules/sources.html#generic-git-repository
apt install -y --no-install-recommends \
    curl/stable \
    git/stable \
    libdigest-sha-perl/stable \
    unzip/stable
rm -rf /var/lib/apt/lists/*
# Reason: To put raw string into ~/.bashrc .
# hadolint ignore=SC2016
curl -O -L https://github.com/tofuutils/tenv/releases/download/${TENV_VERSION}/tenv_${TENV_VERSION}_${BUILDARCH}.deb
dpkg -i tenv_${TENV_VERSION}_${BUILDARCH}.deb
tenv completion bash > ~/.tenv.completion.bash
echo 'source ${HOME}/.tenv.completion.bash' >> ~/.bashrc
export TENV_AUTO_INSTALL=true
