import sys
sys.path.insert(0, 'tests')
import test_issue7955_route_js as t
d = t.DRIVER.replace(
    "console.log(JSON.stringify(result));",
    "if(input.action==='custom'){result=eval(input.code);}\nconsole.log(JSON.stringify(result));")
open(sys.argv[1], 'w').write(d)
print('ok')
