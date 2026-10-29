# TMDB 响应样例

自动化测试用，不调真实接口（`process.md` 第 4 节）。按 TMDB 官方接口的返回格式手工整理，
只保留程序用到的字段。*Planet Earth II*（68595）、*NOVA*（3562）、*Horizon*（1966）、
*Inside the Factory*（72793）的编号是真实的，其余（9001xx、9002xx）是虚构的测试条目；内容都做了简化，不要当真实数据用。

文件名对应请求（`tests/tmdb_mock.py`）：

| 文件 | 请求 |
|---|---|
| `discover-networks-<编号>-p<页>.json` | `discover/tv?with_networks=<编号>&page=<页>` |
| `discover-companies-<编号>-p<页>.json` | `discover/tv?with_companies=<编号>&page=<页>` |
| `tv-<编号>.json` | `tv/<编号>?append_to_response=keywords,external_ids,translations` |
| `season-<编号>-<季号>.json` | `tv/<编号>/season/<季号>` |

真实返回和样例对不上导致出错时，按真实返回补一份样例，再加一条测试。
