import sys

with open(r'c:\Users\andrea.mazzarotto\myJobs\SynthTrade\synthtrade\backend\app\execution\okx_exchange.py', 'rb') as f:
    content = f.read().decode('utf-8')

old_code = '''            if data.get("code") != "0":
                s_code = data.get("sCode")
                s_msg = data.get("sMsg")
                raise RuntimeError(
                    f"OKX API error {data.get('code')}: {data.get('msg')} "
                    f"| sCode={s_code} sMsg={s_msg} | full_data={data}"
                )

            return data.get("data", [{}])[0]'''.replace('\r\n', '\n')

new_code = '''            if data.get("code") != "0":
                s_code = data.get("sCode")
                s_msg = data.get("sMsg")
                raise RuntimeError(
                    f"OKX API error {data.get('code')}: {data.get('msg')} "
                    f"| sCode={s_code} sMsg={s_msg} | full_data={data}"
                )

            result = data.get("data", [{}])[0]
            if result.get("sCode", "0") != "0":
                raise RuntimeError(
                    f"OKX Order failed with sCode={result.get('sCode')}: {result.get('sMsg')} "
                    f"| full_data={data}"
                )

            return result'''.replace('\r\n', '\n')

content_normalized = content.replace('\r\n', '\n')

if old_code in content_normalized:
    content_normalized = content_normalized.replace(old_code, new_code)
    with open(r'c:\Users\andrea.mazzarotto\myJobs\SynthTrade\synthtrade\backend\app\execution\okx_exchange.py', 'wb') as f:
        f.write(content_normalized.encode('utf-8'))
    print('Patched successfully!')
else:
    print('Could not find exact block to replace.')
