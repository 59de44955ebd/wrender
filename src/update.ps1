[System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms") | out-null

[string]$app_name = $args[0]
[float]$version = $args[1]
[string]$base_url = $args[2]
[string]$setup_exe = $args[3]

try {
	$tag = ([array]([xml](Invoke-WebRequest -UseBasicParsing "$base_url/tags.atom").Content).feed.entry)[0].title
	if($tag.Substring(1) -gt $version)
	{
		If ($setup_exe -eq "")
		{
			$msgboxresult = [System.Windows.Forms.MessageBox]::Show("A newer version was found. Download it now?", "Update Checker", 4, [System.Windows.Forms.MessageBoxIcon]::Question)
			If ($msgboxresult -eq "Yes")
			{
				Start-Process "$base_url/releases/$tag"
			}
		}
		else
		{
			$msgboxresult = [System.Windows.Forms.MessageBox]::Show("A newer version was found. Do you want to install it now?`n`nAnswering 'Yes' will quit the application.", "Update Checker", 4, [System.Windows.Forms.MessageBoxIcon]::Question)
			If ($msgboxresult -eq "Yes")
			{
			    (Get-Process "$app_name").CloseMainWindow() | out-null
				Invoke-WebRequest -Uri "$base_url/releases/download/$tag/$setup_exe" -OutFile "$Env:TMP\$setup_exe"
				Start-Process -FilePath "$Env:TMP\$setup_exe"
			}
		}
	}
	else
	{
		[System.Windows.Forms.MessageBox]::Show("You are already using the latest version.", "Update Checker", 0, [System.Windows.Forms.MessageBoxIcon]::Information) | out-null
	}
} catch [System.Net.WebException], [System.IO.IOException] {
    [System.Windows.Forms.MessageBox]::Show("Update server not found.`n`nPlease check your internet connection or try again later.", "Update Checker", 0, [System.Windows.Forms.MessageBoxIcon]::Error)
}
