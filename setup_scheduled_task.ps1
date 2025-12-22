# PowerShell 스크립트: SMC 데이터 수집기 작업 스케줄러 등록

# 스크립트 실행 정책 확인 및 변경 (필요 시)
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

# --- 변수 정의 ---
$taskName = "SMC_Data_Collector_And_Archiver"
$taskDescription = "SMC 프로젝트의 실시간 데이터를 10분마다 수집하고 아카이빙합니다."
$batchPath = "$PSScriptRoot\run_collector.bat"
$workingDirectory = "$PSScriptRoot"

# --- 작업 동작(Action) 정의 ---
# 실행할 프로그램과 인자를 설정합니다.
$action = New-ScheduledTaskAction -Execute $batchPath -WorkingDirectory $workingDirectory

# --- 작업 트리거(Trigger) 정의 ---
# 10분마다 무기한 반복되도록 설정합니다.
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 10)

# --- 작업 설정(Settings) 정의 ---
# 추가적인 실행 규칙을 설정합니다.
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -DontStopOnIdleEnd

# --- 작업 주체(Principal) 정의 ---
# 현재 사용자로 작업을 실행하도록 설정합니다.
$principal = New-ScheduledTaskPrincipal -UserId (Get-CimInstance -ClassName Win32_ComputerSystem).UserName -LogonType Interactive

# --- 작업 스케줄러에 등록 ---
Write-Host "작업 스케줄러에 '$taskName' 작업을 등록합니다..."

try {
    # 기존에 같은 이름의 작업이 있다면 삭제
    Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false
    Write-Host "기존 '$taskName' 작업을 삭제했습니다."
} catch {
    # 작업이 없는 경우이므로 아무것도 하지 않음
}

try {
    # 새로운 작업 등록
    Register-ScheduledTask -TaskName $taskName -Description $taskDescription -Action $action -Trigger $trigger -Settings $settings -Principal $principal -ErrorAction Stop
    Write-Host "성공: '$taskName' 작업이 스케줄러에 성공적으로 등록되었습니다."
    Write-Host "이제 10분마다 데이터 수집이 자동으로 실행됩니다."
} catch {
    Write-Error "오류: 작업을 등록하지 못했습니다. 스크립트를 '관리자 권한으로 실행'했는지 확인하세요."
    Write-Error $_
}

# --- 확인 ---
Write-Host ""
Write-Host "등록된 작업 정보 확인:"
Get-ScheduledTask | ? {$_.TaskName -like "SMC*"} | Format-Table -AutoSize
