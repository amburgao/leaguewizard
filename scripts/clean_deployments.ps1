<#
.SYNOPSIS
    Cleans up old GitHub Pages deployments for a specific branch.

.DESCRIPTION
    This script removes all but the most recent GitHub deployment for a specified
    environment (branch). It uses the GitHub CLI (`gh`) to interact with the GitHub
    API. This is useful for managing deployments created by CI/CD workflows, such
    as GitHub Actions for GitHub Pages, preventing an accumulation of old
    deployments.

.PARAMETER GitUsername
    The GitHub username or organization that owns the repository.

.PARAMETER ProjectName
    The name of the repository.

.PARAMETER TargetBranch
    The branch that corresponds to the deployment environment to clean up. For
    GitHub Pages, this is often 'gh-pages'.

.EXAMPLE
    .\clean_deployments.ps1 -GitUsername "my-user" -ProjectName "my-repo" `
        -TargetBranch "gh-pages"

    This command deletes all but the latest deployment for the 'gh-pages'
    environment in the 'my-user/my-repo' repository.
#>
param([string]$GitUsername, [string]$ProjectName, [string]$TargetBranch)

$BaseURL = "repos/$GitUsername/$ProjectName"

$AllDeployments = gh api $BaseURL/deployments | ConvertFrom-Json
$TargetDeployments = $AllDeployments | Where-Object { $_.environment -eq $TargetBranch } | Sort-Object created_at -Descending

$OldDeployments = $TargetDeployments | Select-Object -Skip 1

foreach ($Deploy in $OldDeployments)
{
    gh api $BaseURL/deployments/$($Deploy.id) -X DELETE
    Write-Output "Deleted gh-pages deployment ID $($Deploy.id)"
}
