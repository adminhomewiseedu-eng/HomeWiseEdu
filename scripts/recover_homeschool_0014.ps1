<# Future approval only. Never run automatically from a build, release or migration hook. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{40}$')][string]$RecoveryCommit,
    [switch]$ApprovedForRecovery,
    [switch]$Schema0014Verified,
    [string]$Railway = 'C:\Users\DELL\AppData\Local\HomeWiseEduBackupTools\railway\railway.exe'
)
$ErrorActionPreference = 'Stop'
if (-not $ApprovedForRecovery -or -not $Schema0014Verified) {
    throw 'Separate recovery deployment approval and verified schema 0014 are required. No operation performed.'
}
$project = 'bc3971d4-2ba1-4644-9a1d-241243f91be0'
$environment = 'f22a49df-1a16-4171-b498-29844997a398'
$backend = 'ec8adde3-9dcc-4fd1-ac05-b9b85e03756c'
$frontend = 'e60acc7d-b207-4c19-a846-46ce94dac337'
$previous = 'c550437d0744ad4a50fafca6a640bce8db6895bd'
$feature = 'ea6a625a6bd5d34050fa5acd01414b156eb15f6d'
function Invoke-RailwayQuery([string]$Query) {
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo.FileName = $Railway
    $process.StartInfo.Arguments = 'api -f -'
    $process.StartInfo.UseShellExecute = $false
    $process.StartInfo.CreateNoWindow = $true
    $process.StartInfo.RedirectStandardInput = $true
    $process.StartInfo.RedirectStandardOutput = $true
    $process.StartInfo.RedirectStandardError = $true
    try {
        if (-not $process.Start()) { throw 'Railway API process did not start.' }
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        $process.StandardInput.WriteLine($Query)
        $process.StandardInput.Close()
        if (-not $process.WaitForExit(45000)) {
            $process.Kill()
            throw 'Railway API request timed out; no automatic retry.'
        }
        $process.Refresh()
        $exitCode = $process.ExitCode
        if (-not $stdout.Wait(5000) -or -not $stderr.Wait(5000)) { throw 'Railway API output did not close.' }
        if ($exitCode -ne 0) { throw 'Railway API operation failed; inspect sanitized logs separately.' }
        $raw = $stdout.Result
    } finally {
        if ($process.Id -and -not $process.HasExited) { $process.Kill() }
        $process.Dispose()
    }
    $response = $raw | ConvertFrom-Json
    if ($response.errors) { throw 'Railway API returned errors; stopped without automatic retry.' }
    return $response.data
}
function Wait-Deployment([string]$Id, [string]$ExpectedCommit) {
    $deadline = [DateTime]::UtcNow.AddMinutes(15)
    while ([DateTime]::UtcNow -lt $deadline) {
        $data = Invoke-RailwayQuery ('{deployment(id:"'+$Id+'"){id status meta}}')
        $deployment = $data.deployment
        if ($deployment.meta.commitHash -and $deployment.meta.commitHash -cne $ExpectedCommit) {
            throw 'Deployment SHA mismatch. Stop; never substitute a branch tip.'
        }
        Write-Host ('Deployment '+$Id+': '+$deployment.status)
        if ($deployment.status -eq 'SUCCESS') {
            if ($deployment.meta.commitHash -cne $ExpectedCommit) { throw 'Successful deployment SHA not verified.' }
            return
        }
        if ($deployment.status -in @('FAILED','CRASHED','REMOVED','SKIPPED','CANCELED')) {
            throw 'Recovery deployment failed. Do not retry, downgrade or restore the database automatically.'
        }
        Start-Sleep -Seconds 8
    }
    throw 'Deployment verification timed out. Do not issue another deployment automatically.'
}
function Assert-Http([string]$Url) {
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 30
    if ([int]$response.StatusCode -ne 200) { throw 'Public health check failed.' }
}
# All configuration reads stay in memory. No secret values are printed or saved.
$remote = & git ls-remote https://github.com/adminhomewiseedu-eng/HomeWiseEdu.git refs/heads/codex/homeschool-0014-recovery
if ($LASTEXITCODE -ne 0 -or ($remote -split '\s+')[0] -cne $RecoveryCommit) {
    throw 'Published client recovery branch does not match the pinned recovery commit.'
}
$query = '{ project(id:"'+$project+'"){name} backend:serviceInstance(environmentId:"'+$environment+'",serviceId:"'+$backend+'") {source{repo} rootDirectory builder railwayConfigFile preDeployCommand startCommand healthcheckPath} frontend:serviceInstance(environmentId:"'+$environment+'",serviceId:"'+$frontend+'") {source{repo} rootDirectory railwayConfigFile preDeployCommand latestDeployment{id status meta}} environmentStagedChanges(environmentId:"'+$environment+'"){patch} variables(projectId:"'+$project+'",environmentId:"'+$environment+'",serviceId:"'+$backend+'",unrendered:true) }'
$data = Invoke-RailwayQuery $query
if ($data.project.name -cne 'HomeWiseEdu') { throw 'Project identity mismatch.' }
$b = $data.backend
if ($b.source.repo -cne 'adminhomewiseedu-eng/HomeWiseEdu' -or
    $b.rootDirectory -notin @($null,'','/') -or $b.builder -ne 'RAILPACK' -or
    $b.railwayConfigFile -or @($b.preDeployCommand | Where-Object { $null -ne $_ -and [string]$_ -ne '' }).Count -gt 0 -or
    $b.startCommand -cne 'uvicorn backend.main:app --host 0.0.0.0 --port $PORT' -or
    $b.healthcheckPath -cne '/ready') { throw 'Backend configuration drift; no deployment performed.' }
if ($data.variables.DATABASE_URL -cne '${{Postgres.DATABASE_URL}}' -or
    $data.variables.AUTO_INIT_DB -cne 'false') { throw 'Database reference/initialization configuration drift.' }
if ($data.environmentStagedChanges.patch -and
    ($data.environmentStagedChanges.patch | ConvertTo-Json -Depth 30 -Compress) -ne '{}') {
    throw 'Pending configuration changes exist. Do not apply them through recovery.'
}
$f = $data.frontend
if ($f.source.repo -cne 'adminhomewiseedu-eng/HomeWiseEdu' -or $f.rootDirectory -cne '/frontend' -or
    $f.railwayConfigFile -or @($f.preDeployCommand | Where-Object { $null -ne $_ -and [string]$_ -ne '' }).Count -gt 0) { throw 'Frontend configuration drift.' }
$frontSha = $f.latestDeployment.meta.commitHash
if ($frontSha -notin @($previous,$feature)) { throw 'Unexpected frontend revision; request a reviewed recovery plan.' }
# The recovery backend intentionally has no assignment/browser API. Restore the old UI if needed.
if ($frontSha -eq $feature) {
    $result = Invoke-RailwayQuery ('mutation {serviceInstanceDeployV2(environmentId:"'+$environment+'",serviceId:"'+$frontend+'",commitSha:"'+$previous+'")}')
    Wait-Deployment $result.serviceInstanceDeployV2 $previous
    Assert-Http 'https://homewiseedu.com'
}
$result = Invoke-RailwayQuery ('mutation {serviceInstanceDeployV2(environmentId:"'+$environment+'",serviceId:"'+$backend+'",commitSha:"'+$RecoveryCommit+'")}')
$deploymentId = $result.serviceInstanceDeployV2
Write-Host ('Recovery backend deployment ID: '+$deploymentId)
Wait-Deployment $deploymentId $RecoveryCommit
Assert-Http 'https://homewiseedu-production-9083.up.railway.app/health'
Assert-Http 'https://homewiseedu-production-9083.up.railway.app/ready'
Assert-Http 'https://homewiseedu.com'
Write-Host 'Recovery deployed and public health checks passed. Schema retained; no migration or seed command executed by this script.'
Write-Host 'Review sanitized logs and use approved accounts for authenticated checks. No QA records were created.'
