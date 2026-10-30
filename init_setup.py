import sys
import subprocess
import os

def init_environment():
    # 1. Config streamlit to avoid email prompt
    user_profile = os.environ.get('USERPROFILE', os.path.expanduser('~'))
    streamlit_dir = os.path.join(user_profile, '.streamlit')
    os.makedirs(streamlit_dir, exist_ok=True)
    
    cred_file = os.path.join(streamlit_dir, 'credentials.toml')
    with open(cred_file, 'w', encoding='utf-8') as f:
        f.write('[general]\nemail = ""\n')
        
    cfg_file = os.path.join(streamlit_dir, 'config.toml')
    with open(cfg_file, 'w', encoding='utf-8') as f:
        f.write('[browser]\ngatherUsageStats = false\n[server]\nheadless = false\n')

    # 2. Check and install missing libraries
    required_packages = ['streamlit', 'pandas', 'openpyxl', 'playwright', 'playwright_stealth', 'beautifulsoup4', 'plyer']
    missing = []
    for pkg in required_packages:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
            
    if missing:
        print(f"Installing missing dependencies: {', '.join(missing)}...")
        req_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'requirements.txt')
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', req_file, '--disable-pip-version-check'])
        
        print("Installing browser engine (Playwright Chromium)...")
        subprocess.check_call([sys.executable, '-m', 'playwright', 'install', 'chromium'])

    # 3. Create Desktop shortcuts if missing
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders')
        desktop_path, _ = winreg.QueryValueEx(key, 'Desktop')
        desktop_path = os.path.expandvars(desktop_path)
        cur_dir = os.path.abspath(os.path.dirname(__file__))
        
        vbs = f'''
        Set oWS = WScript.CreateObject("WScript.Shell")
        sLink = "{desktop_path}\\Washers_Georgievsk.lnk"
        Set oLink = oWS.CreateShortcut(sLink)
        oLink.TargetPath = "wscript.exe"
        oLink.Arguments = """{cur_dir}\\run_silent.vbs"""
        oLink.WorkingDirectory = "{cur_dir}"
        oLink.Description = "Стиральные машины Георгиевск"
        oLink.IconLocation = "shell32.dll,13"
        oLink.Save

        sLink2 = "{desktop_path}\\Price_Monitor_Georgievsk.lnk"
        Set oLink2 = oWS.CreateShortcut(sLink2)
        oLink2.TargetPath = "{cur_dir}\\start_monitor.bat"
        oLink2.WorkingDirectory = "{cur_dir}"
        oLink2.Description = "Мониторинг цен Георгиевск"
        oLink2.IconLocation = "shell32.dll,175"
        oLink2.Save
        '''
        vbs_path = os.path.join(cur_dir, '_make_sc.vbs')
        with open(vbs_path, 'w', encoding='cp1251') as f:
            f.write(vbs)
        subprocess.run(['cscript', '//nologo', vbs_path], capture_output=True)
        if os.path.exists(vbs_path):
            os.remove(vbs_path)
    except Exception:
        pass

    print("Setup completed successfully!")

if __name__ == '__main__':
    init_environment()
