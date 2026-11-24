import re, subprocess, sys, os
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = r'E:\01地下電廠洞室開挖支撐設計分析\Simulation_StudyWeb\ch5_mohrcoulomb.html'
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'

src = open(os.path.join(HERE, 'mc_model.js'), encoding='utf-8').read()
model = src[src.index('// MODEL-START'):src.index('// MODEL-END') + len('// MODEL-END')]
t = open(os.path.join(HERE, 'ch5_template.html'), encoding='utf-8').read()
out = t.replace('/*__MODEL__*/', model)
open(OUT, 'w', encoding='utf-8').write(out)
open(os.path.join(HERE, 'inline.js'), 'w', encoding='utf-8').write('\n'.join(re.findall(r'<script>(.*?)</script>', out, re.S)))
print('built', len(out))

def shot(name, hide, inject='', h=3600, crop=None):
    s = out.replace('<head>', '<head><base href="file:///E:/01地下電廠洞室開挖支撐設計分析/Simulation_StudyWeb/">', 1)
    s = s.replace('</style>', hide + '{display:none!important}</style>', 1)
    s = s.replace('</body>', f'<script>{inject}</script></body>')
    fn = os.path.join(HERE, f'v_{name}.html'); open(fn, 'w', encoding='utf-8').write(s)
    png = os.path.join(HERE, f'p_{name}.png')
    subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--virtual-time-budget=6000', f'--window-size=1500,{h}',
                    f'--screenshot={png}', 'file:///' + fn.replace('\\', '/')], capture_output=True)
    im = Image.open(png)
    if crop: im.crop(crop).save(png)
    return png

if __name__ == '__main__':
    hide_all_but_lab = 'header.hero,#s1,#s2,#s3,#s4,#s5,#s7,#s8,#s9,#s10,#s11,#s12,#s13,#s6>p,#s6>h3,#s6>.tablewrap,#s6>details'
    for k in [int(x) for x in sys.argv[1:]]:
        shot(f'pre{k}', hide_all_but_lab, f"document.querySelectorAll('#presets .btn')[{k}].click();", h=2100, crop=(268, 380, 1500, 2100))
