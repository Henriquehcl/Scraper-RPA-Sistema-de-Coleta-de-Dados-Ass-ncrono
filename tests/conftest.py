"""
Fixtures globais de teste compartilhadas entre testes unitários e de integração.
"""

import asyncio
import uuid

import pytest


# ──────────────────────────────────────────────────────────────
# Configuração do event loop para pytest-asyncio
# ──────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def event_loop():
    """Cria um event loop único para toda a sessão de testes."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ──────────────────────────────────────────────────────────────
# Dados de exemplo para Hockey
# ──────────────────────────────────────────────────────────────
@pytest.fixture
def sample_hockey_html() -> str:
    """HTML de exemplo com estrutura da tabela de hockey."""
    return """
    <html><body>
    <table class="table">
      <tbody>
        <tr class="team">
          <td>Boston Bruins</td>
          <td>2011</td>
          <td>46</td>
          <td>25</td>
          <td>11</td>
          <td>0.561</td>
          <td>246</td>
          <td>229</td>
          <td>17</td>
        </tr>
        <tr class="team">
          <td>Montreal Canadiens</td>
          <td>2011</td>
          <td>44</td>
          <td>30</td>
          <td>8</td>
          <td>0.537</td>
          <td>212</td>
          <td>226</td>
          <td>-14</td>
        </tr>
      </tbody>
    </table>
    <ul class="pagination">
      <li class="page-item"><a class="page-link" href="?page_num=1">1</a></li>
    </ul>
    </body></html>
    """


# ──────────────────────────────────────────────────────────────
# Dados de exemplo para Oscar
# ──────────────────────────────────────────────────────────────
@pytest.fixture
def sample_oscar_records() -> list[dict]:
    """Registros de filme do Oscar para uso em testes."""
    return [
        {
            "year": 2010,
            "title": "The Hurt Locker",
            "nominations": 9,
            "awards": 6,
            "best_picture": True,
        },
        {
            "year": 2010,
            "title": "Avatar",
            "nominations": 9,
            "awards": 3,
            "best_picture": False,
        },
    ]


# ──────────────────────────────────────────────────────────────
# UUID de job para testes
# ──────────────────────────────────────────────────────────────
@pytest.fixture
def job_id() -> uuid.UUID:
    """UUID fixo para uso em testes."""
    return uuid.UUID("12345678-1234-5678-1234-567812345678")
