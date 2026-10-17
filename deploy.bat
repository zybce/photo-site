@echo off
rem 一键发布：重新生成页面并推送到 GitHub（Cloudflare Pages 会自动部署）
rem 推送默认直连；直连失败时自动临时走一次代理（用完即弃，不写入 git 配置）
set PROXY=http://192.168.1.200:7890
cd /d %~dp0
C:\ProgramData\miniconda3\envs\image\python.exe build.py || goto :err
git add -A
git diff --cached --quiet && (echo 没有内容变更，跳过提交) || git commit -m "更新站点内容"
git push && goto :ok
echo.
echo 直连推送失败，临时走代理 %PROXY% 重试一次...
git -c http.proxy=%PROXY% push || goto :err
:ok
echo.
echo 发布完成，Cloudflare Pages 约 1-2 分钟后生效。
pause
exit /b 0
:err
echo.
echo 出错了，把上面的报错信息发给我排查。
pause
exit /b 1
