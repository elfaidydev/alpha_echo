import os

def fix_po_file(filepath, lang):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    header_lines = [
        '# Translation of Odoo Server.',
        '# This file contains the translation of the following modules:',
        '# \t* alpha_echo',
        '#',
        'msgid ""',
        'msgstr ""',
        '"Project-Id-Version: Odoo Server 17.0\\n"',
        '"Report-Msgid-Bugs-To: \\n"',
        '"POT-Creation-Date: 2026-02-28 20:48+0000\\n"',
        '"PO-Revision-Date: 2026-02-28 20:48+0000\\n"',
        '"Last-Translator: \\n"',
        '"Language-Team: \\n"',
        '"MIME-Version: 1.0\\n"',
        '"Content-Type: text/plain; charset=UTF-8\\n"',
        '"Content-Transfer-Encoding: \\n"',
        f'"Language: {lang}\\n"',
        '"Plural-Forms: \\n"',
        '',
        ''
    ]
    header = "\n".join(header_lines)
    
    # split and find actual msgid entry
    msg_start = content.find('#. module:')
    if msg_start == -1:
        msg_start = content.find('#:')
    if msg_start == -1:
        # Use first non-empty msgid
        import re
        m = re.search(r'\n(msgid \".+\")', content)
        if m:
            msg_start = m.start() + 1
        
    if msg_start != -1:
        body = content[msg_start:]
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(header)
            f.write(body)
        print(f'Successfully fixed {filepath}')
    else:
        print(f'Could not find actual messages in {filepath}')

fix_po_file('/Users/abdelazim.dev/Projects/odoo-projects/odoo-v17/custom_addons/MANZOR/addons/alpha_echo/i18n/ar_EG.po', 'ar_EG')
fix_po_file('/Users/abdelazim.dev/Projects/odoo-projects/odoo-v17/custom_addons/MANZOR/addons/alpha_echo/i18n/ar.po', 'ar')
