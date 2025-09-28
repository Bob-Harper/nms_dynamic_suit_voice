param(
    [string]$url,
    [string]$outfile
)
Invoke-WebRequest -Uri $url -OutFile $outfile
