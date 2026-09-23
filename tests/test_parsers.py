import pytest

from emule_mcp.errors import InvalidLinkError, ParseError
from emule_mcp.parsers import (
    extract_ed2k_hash,
    extract_session,
    parse_downloads,
    parse_search,
    parse_servers,
    parse_status,
)

HEADER = """
<html><body>
<table>
<tr>
<td><a href="?ses=42&amp;w=kad"><img src="h_kad.gif"><br />Kad</a></td>
</tr>
</table>
<table>
<tr>
<td><img src="high.gif" align="left"> DonkeyServer No1 &nbsp;&nbsp;(<img src="l_users.gif" align="middle"> 1.234&nbsp;&nbsp;<img src="filetype_other.gif" align="middle"> 56.789)</td>
<td width="25%" nowrap><img src="h_kad.gif" width="16" height="16" align="left"> Conectado (<a href="?ses=42&w=kad&c=disconnect">Desconectar</a>)</td>
</tr>
<tr>
<td style="font-size: 8pt"><img src="arrow_down.gif" align="left" hspace="3" vspace="4"> Bajada: 12.3 KB/s (100.0 KB/s)
<table width="125"><tr><td><img src="qs_down.jpg" width="12.3%" height="8"></td></tr></table></td>
<td style="font-size: 8pt"><img src="arrow_up.gif" align="left" hspace="3" vspace="4"> Subida: 4.5 KB/s (50.0 KB/s)</td>
</tr>
</table>
</body></html>
"""

SEARCH_RESULT = """
<html><body>
<td colspan="6" class="search-main"><img src="l_filesearch.gif"><b><a href="#">Result</a>&nbsp;<a href="?ses=42&amp;w=search"><font color="#FFC412">(Searching...)</font></a></b></td>
<table>
<tr>
<td class="search-line-left"><table cellspacing="0" cellpadding="0" border="0" valign=middle class="search-line"><tr><td background="l_sources_5.gif" width="16" height="16"><a href="#" onMouseover="searchmenu(event,'ed2k://|file|Marc Anthony - Vivir Mi Vida.mp3|4500000|ABCDEF0123456789ABCDEF0123456789|/')" onMouseout="delayhidemenu()"><img src="is_none.gif"></a></td><td>&nbsp;<img src="filetype_audio.gif" align="middle"></td><td>&nbsp;</td>
<td><font color=#ffffff>Marc Anthony - Vivir Mi Vida.mp3</font></td>
</tr></table></td>
<td class="search-line-right"><font color=#ffffff>4.29 MB</font></td>
<td class="search-line" style="font-size: 7.5pt"><font color=#ffffff>ABCDEF0123456789ABCDEF0123456789</font></td>
<td class="search-line" style="font-size: 7.5pt"><font color=#ffffff>7(3)</font></td>
<td class="search-line"><input type="checkbox" name="downloads" value="ABCDEF0123456789ABCDEF0123456789"></td>
</tr>
<tr><td colspan="6" bgcolor="#005784" height="1"></td></tr>
</table>
</body></html>
"""


def test_extract_session_from_link():
    assert extract_session('<a href="?ses=123456&w=transfer">x</a>') == "123456"


def test_extract_session_returns_none_on_login_page():
    assert extract_session("<html><body>please log in</body></html>") is None


def test_parse_status_reads_connection_state():
    status = parse_status(HEADER)
    assert status.connection_state == "high"
    assert "DonkeyServer No1" in status.connection_text


def test_parse_status_reads_rates_and_kad():
    status = parse_status(HEADER)
    assert status.download == "12.3 KB/s (100.0 KB/s)"
    assert status.upload == "4.5 KB/s (50.0 KB/s)"
    assert status.kad.startswith("Conectado")


def test_parse_status_fails_without_state_image():
    with pytest.raises(ParseError):
        parse_status("<html><body>unexpected payload</body></html>")


def test_parse_search_reads_result_line():
    outcome = parse_search(SEARCH_RESULT)
    assert outcome.message == "Searching..."
    assert len(outcome.results) == 1

    result = outcome.results[0]
    assert result.name == "Marc Anthony - Vivir Mi Vida.mp3"
    assert result.size == "4.29 MB"
    assert result.file_hash == "ABCDEF0123456789ABCDEF0123456789"
    assert result.sources == "7(3)"
    assert result.ed2k == (
        "ed2k://|file|Marc Anthony - Vivir Mi Vida.mp3|4500000|ABCDEF0123456789ABCDEF0123456789|/"
    )


def test_parse_search_without_results_is_empty():
    outcome = parse_search("<html><body><font color=\"#FFC412\">(Please search)</font></body></html>")
    assert outcome.results == ()


SERVER_LIST = """
<html><body>
<table>
<tr>
 <td valign=middle class="server-line-high-left"><table cellspacing="0" cellpadding="0" border="0" class="server-line-high-left"><tr><td background="high.gif" width="16" height="16"><a href="#" onMouseover="servermenu(event,'admin','ed2k://|server|85.10.200.10|4661|/','42','85.10.200.10','4661','staticsrv')" onMouseout="delayhidemenu()"><img src="is_static.gif"></a></td><td>&nbsp;</td><td>eMule Security</td></tr></table></td>
 <td valign=middle class="server-line-high">85.10.200.10:4661</td>
 <td valign=middle class="server-line-high">Server description</td>
 <td valign=middle class="server-line-high">25</td>
 <td valign=middle class="server-line-high">1.2 M (2.0 M)</td>
 <td valign=middle class="server-line-high">15.3 M</td>
 <td valign=middle class="server-line-high"><a href="#" onMouseover="serverpriomenu(event,'admin','42','85.10.200.10','4661','High')" onMouseout="delayhidemenu()">Alta</a></td>
 <td valign=middle class="server-line-high">0</td>
 <td valign=middle class="server-line-high">5000 (5000)</td>
 <td valign=middle class="server-line-high">17.15</td>
 <td valign=middle class="server-line-high"><img src="checked.gif"></td>
</tr>
</table>
</body></html>
"""


def test_parse_servers_reads_row():
    servers = parse_servers(SERVER_LIST)
    assert len(servers) == 1

    server = servers[0]
    assert server.name == "eMule Security"
    assert server.ip == "85.10.200.10"
    assert server.port == "4661"
    assert server.state == "high"
    assert server.users == "1.2 M (2.0 M)"
    assert server.files == "15.3 M"
    assert server.priority == "High"


def test_parse_servers_without_rows_is_empty():
    assert parse_servers("<html><body><table></table></body></html>") == ()


TRANSFER_LIST = """
<html><body>
<table border=0 align=center cellpadding=4 cellspacing=0 width="95%">
<tr>
 <td align=center valign=middle>
<table border=0 align=center cellpadding=2 cellspacing=0 width="100%" bgcolor="#99CCFF">
<tr>
 <td class="down-header-left">Download</td>
</tr>
<tr>
 <td valign=top class="down-line-downloading-left" nowrap><table cellspacing="0" cellpadding="0" border="0" valign=top class="down-line-downloading-left">
 <tr><td>
 <a href="#" onMouseover="downmenu(event,'admin','Ubuntu.iso','ed2k://|file|Ubuntu.iso|4500000|ABCDEF0123456789ABCDEF0123456789|/','downloading','disabled','Ubuntu.iso','42','ABCDEF0123456789ABCDEF0123456789','','yes')" onMouseout="delayhidemenu()">
 <img src="t_downloading.gif"></a>
 </td>
 <td>&nbsp;</td>
 <td background="filetype_Pro.gif" width="16" height="16" style="background-position:center;background-repeat:no-repeat">
 <img src="is_halfnone.gif"></td><td>&nbsp;</td><td onMouseover="doTooltip(event, this.firstChild.innerHTML)" onMouseout="hideTip()"><div style="display: none;">Complete: 4500000</div>Ubuntu.iso</td></tr></table></td>
 <td valign=top class="down-line-downloading-right" nowrap style="font-size: 7.5pt">4.29 MB</td>
 <td valign=top class="down-line-downloading-right" nowrap>1.00 MB</td>
 <td valign=middle class="down-line-downloading" width=125><table width=125 height=11 border=1 class="percent_table" cellpadding=0 cellspacing=0 bordercolor="#000000"><tr><td><img src="downbar.gif"></td></tr></table></td>
 <td valign=top class="down-line-downloading-right" nowrap>12.30</td>
 <td valign=top class="down-line-downloading" nowrap style="font-size: 7.5pt">5&nbsp;/&nbsp;10&nbsp;(2)</td>
 <td valign=top class="down-line-downloading" nowrap style="font-size: 7.5pt"><a href="#" onMouseover="downpriomenu(event,'admin','42','ABCDEF0123456789ABCDEF0123456789','Normal','downloading')" onMouseout="delayhidemenu()">Normal</a></td>
 <td valign=top class="down-line-downloading" style="font-size: 7.5pt"><a href="#" onMouseover="showmenu(event,'','downloading')" onMouseout="delayhidemenu()">Default</a></td>
 <td valign=top class="down-line-downloading" width="9" style="font-size: 7.5pt"><img src="checked_no.gif"></td>
</tr>
<tr>
 <td colspan="10" bgcolor="#005784" height="1"></td>
</tr>
<tr>
 <td valign=top class="down-line-paused-left" nowrap><table cellspacing="0" cellpadding="0" border="0" valign=top class="down-line-paused-left">
 <tr><td>
 <a href="#" onMouseover="downmenu(event,'admin','Otro.mp3','ed2k://|file|Otro.mp3|4500000|11111111111111111111111111111111|/','paused','disabled','Otro.mp3','42','11111111111111111111111111111111','','yes')" onMouseout="delayhidemenu()">
 <img src="t_paused.gif"></a>
 </td>
 <td>&nbsp;</td>
 <td background="filetype_Audio.gif" width="16" height="16" style="background-position:center;background-repeat:no-repeat">
 <img src="is_halfnone.gif"></td><td>&nbsp;</td><td onMouseover="doTooltip(event, this.firstChild.innerHTML)" onMouseout="hideTip()"><div style="display: none;">Complete: 0</div>Otro.mp3</td></tr></table></td>
 <td valign=top class="down-line-paused-right" nowrap style="font-size: 7.5pt">4.29 MB</td>
 <td valign=top class="down-line-paused-right" nowrap>-</td>
 <td valign=middle class="down-line-paused" width=125><table width=125 height=11 border=1 class="percent_table" cellpadding=0 cellspacing=0 bordercolor="#000000"><tr><td><img src="downbar.gif"></td></tr></table></td>
 <td valign=top class="down-line-paused-right" nowrap>-</td>
 <td valign=top class="down-line-paused" nowrap style="font-size: 7.5pt">-</td>
 <td valign=top class="down-line-paused" nowrap style="font-size: 7.5pt"><a href="#" onMouseover="downpriomenu(event,'admin','42','11111111111111111111111111111111','Auto','paused')" onMouseout="delayhidemenu()">Auto</a></td>
 <td valign=top class="down-line-paused" style="font-size: 7.5pt"><a href="#" onMouseover="showmenu(event,'','paused')" onMouseout="delayhidemenu()">Default</a></td>
 <td valign=top class="down-line-paused" width="9" style="font-size: 7.5pt"><img src="checked_no.gif"></td>
</tr>
<tr>
 <td valign=middle class="down-header-left" style="font-size: 7.5pt"><b>[TotalDown]</b></td>
</tr>
</table>
 </td>
</tr>
</table>
</body></html>
"""


def test_parse_downloads_reads_rows():
    downloads = parse_downloads(TRANSFER_LIST)
    assert len(downloads) == 2

    first = downloads[0]
    assert first.name == "Ubuntu.iso"
    assert first.size == "4.29 MB"
    assert first.transferred == "1.00 MB"
    assert first.speed == "12.30"
    assert first.sources == "5 / 10 (2)"
    assert first.priority == "Normal"
    assert first.category == "Default"
    assert first.state == "downloading"
    assert first.file_hash == "ABCDEF0123456789ABCDEF0123456789"
    assert first.ed2k == "ed2k://|file|Ubuntu.iso|4500000|ABCDEF0123456789ABCDEF0123456789|/"

    second = downloads[1]
    assert second.name == "Otro.mp3"
    assert second.state == "paused"
    assert second.priority == "Auto"
    assert second.file_hash == "11111111111111111111111111111111"


def test_parse_downloads_without_rows_is_empty():
    assert parse_downloads("<html><body><table></table></body></html>") == ()


def test_extract_ed2k_hash_reads_file_link():
    ed2k = "ed2k://|file|Ubuntu.iso|4500000|ABCDEF0123456789ABCDEF0123456789|/"
    assert extract_ed2k_hash(ed2k) == "ABCDEF0123456789ABCDEF0123456789"


def test_extract_ed2k_hash_rejects_non_file_link():
    with pytest.raises(InvalidLinkError):
        extract_ed2k_hash("ed2k://|server|85.10.200.10|4661|/")
