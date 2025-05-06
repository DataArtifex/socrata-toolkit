$url = "https://data.sfgov.org/resource/vw6y-z8j6"
$apptoken = "YOURAPPTOKENHERE"

# Set header to accept JSON
$headers = New-Object "System.Collections.Generic.Dictionary[[String],[String]]"
$headers.Add("Accept","application/json")
$headers.Add("X-App-Token",$apptoken)

$results = Invoke-RestMethod -Uri $url -Method get -Headers $headers