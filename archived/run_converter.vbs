Set WshShell = CreateObject("WScript.Shell")

' Build the command string
cmdLine = "cmd.exe /c ""C:\PythonScripts\NMS_SUIT_VOICE\sound2wem\zSound2wem.cmd"" --conversion:Vorbis Quality High --out:""C:\Program Files (x86)\Steam\steamapps\common\No Man's Sky\GAMEDATA\MODS\DYNAMIC_SUIT_VOICE\AUDIO\WINDOWS\MEDIA\ENGLISH(US)"" """ & WScript.Arguments(0) & """"

' Run the command minimized (7 = minimized, 0 = hidden)
WshShell.Run cmdLine, 7, True

Set WshShell = Nothing
