import re
content = open('app/api/v1/endpoints/procurement.py', 'r').read()
content = content.replace('deps.get_tenant_id', 'deps.get_optional_scoped_tenant_id')
open('app/api/v1/endpoints/procurement.py', 'w').write(content)
print('Done - replaced all occurrences')
