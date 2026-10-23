"""Restyle the StatiCrypt lock screen in JD dark mode. Usage: python3 brand.py <locked.html> <kit>"""
import sys,base64,glob
p=sys.argv[1]; s=open(p).read()
ff=base64.b64encode(open(glob.glob(sys.argv[2]+'/blobs/872f8638673a9b30a10eb06bf31f09f2.*')[0],'rb').read()).decode()
it=base64.b64encode(open(glob.glob(sys.argv[2]+'/blobs/fdebddcbf42081ff9e6cbbf305b30e2a.*')[0],'rb').read()).decode()
css="""<style>
@font-face{font-family:'JD Forever';src:url(data:font/woff2;base64,%s) format('woff2')}
@font-face{font-family:'JD Inter Tight';src:url(data:font/woff2;base64,%s) format('woff2')}
html.staticrypt-html,body.staticrypt-body{background:#000!important;font-family:'JD Inter Tight',Arial,sans-serif!important}
.staticrypt-form{background:#121212!important;border:1px solid #2E2E2E;border-radius:16px;box-shadow:0 0 40px rgba(255,222,20,.08)!important}
.staticrypt-title{font-family:'JD Forever',Arial,sans-serif!important;text-transform:uppercase;font-size:34px!important;line-height:.95;color:#FFDE14!important;font-weight:400!important}
.staticrypt-instructions p,.staticrypt-form label,.staticrypt-instructions{color:#CCCCCC!important}
.staticrypt-form input[type=password],.staticrypt-form input[type=text]{background:#1B1B1B!important;color:#fff!important;border:1px solid #3D3D3D!important;border-radius:10px}
.staticrypt-decrypt-button{color:#000!important;font-weight:700!important;letter-spacing:.06em;border-radius:999px!important}
.staticrypt-form hr{border-color:#2E2E2E!important}
</style>"""%(ff,it)
s=s.replace('</head>',css+'</head>',1); open(p,'w').write(s)
