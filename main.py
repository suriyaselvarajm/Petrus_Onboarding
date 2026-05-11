"""
main.py — Petrus Technologies Employee Onboarding Portal
Entry point: dependency check → splash → main window.
"""

import tkinter as tk
import sys


def main():
    root = tk.Tk()
    root.withdraw()          # Hide until ready

    # ── Dependency / startup splash ────────────────────────────────────────────
    from gui.splash import SplashScreen
    splash = SplashScreen(root)
    root.wait_window(splash)

    if not splash.success:
        # User closed or critical failure — window may already be destroyed
        try:
            root.destroy()
        except Exception:
            pass
        sys.exit(0)

    # ── Launch main application ────────────────────────────────────────────────
    from gui.app import OnboardingApp
    root.deiconify()
    OnboardingApp(root)
    root.mainloop()


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
