
import os

path = r"c:\Petrus_Onboarding\gui\user_form.py"

with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
in_class = False
for line in lines:
    if line.startswith("class UserForm"):
        in_class = True
        new_lines.append(line)
        continue
    
    if in_class:
        if line.strip() == "":
            new_lines.append(line)
            continue
        # If the line is not indented, indent it by 4 spaces.
        if not line.startswith(" ") and not line.startswith("\t") and not line.startswith("#"):
            new_lines.append("    " + line)
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Indentation fixed")
