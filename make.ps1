# ini から VERSION を取得
$ini = Get-Content .\build.ini
$version = ($ini | Select-String -Pattern "VERSION").ToString().Split("=")[1].Trim()

# スクリプトファイルがある場所に移動する
Set-Location -Path $PSScriptRoot
# 各ファイルを置くフォルダを作成
New-Item -ItemType Directory -Force -Path ".\release_files\"
# ビルドフォルダを削除
Remove-Item -Path .\build -Recurse -Force

# 並列処理内で、処理が重いNerd Fontsのビルドを優先して処理する
$option_and_output_folder = @(
    @("", "-"), # ビルド 通常版
    @("--discord", "Discord-") # ビルド Discord
)

$option_and_output_folder | Foreach-Object -ThrottleLimit 4 -Parallel {
    Write-Host "fontforge script start. option: `"$($_[0])`""
    Invoke-Expression "& `"C:\Program Files (x86)\FontForgeBuilds\bin\ffpython.exe`" .\fontforge_script.py --do-not-delete-build-dir $($_[0])" `
        && Write-Host "fonttools script start. option: `"$($_[1])`"" `
        && python fonttools_script.py $_[1]
}

$move_file_src_dest = @(
    @("BizinGothicDiscord*-*.ttf", "BizinGothicDiscord_$version"),
    @("BizinGothic*-*.ttf", "BizinGothic_$version")
)

$timestamp = Get-Date -Format "yyyyMMddHHmmss"
$move_dir = ".\release_files\build_$timestamp"

$move_file_src_dest | Foreach-Object {
    $folder_path = "$move_dir\$($_[1])"
    New-Item -ItemType Directory -Force -Path $folder_path
    Move-Item -Path ".\build\$($_[0])" -Destination $folder_path -Force
}
