$deployments = gh api repos/amburgao/leaguewizard/deployments | ConvertFrom-Json
$ghPagesDeployments = $deployments | Where-Object { $_.environment -eq "github-pages" } | Sort-Object created_at -Descending

$oldDeployments = $ghPagesDeployments | Select-Object -Skip 1

foreach ($d in $oldDeployments)
{
    gh api repos/amburgao/leaguewizard/deployments/$($d.id) -X DELETE
    Write-Output "Deleted gh-pages deployment ID $($d.id)"
}
