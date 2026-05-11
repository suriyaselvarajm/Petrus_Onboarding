$user = 'suriya.selvaraj'
$pwd = 'Welcome@123'
$sec_auth = ConvertTo-SecureString $pwd -AsPlainText -Force
$cred_auth = New-Object System.Management.Automation.PSCredential ($user, $sec_auth)
try { 
    $u = Get-ADUser -Identity $user -Credential $cred_auth -Server 'petrus.local' -ErrorAction Stop
    Write-Output "Get-ADUser OK"
    Get-ADPrincipalGroupMembership -Identity $user -Credential $cred_auth -Server 'petrus.local' -ErrorAction Stop | Select-Object -ExpandProperty Name
    Write-Output 'OK' 
} catch { 
    Write-Output $_.Exception.Message 
}
