# Arquitetura

```text
                   +----------------------+
script_eng/*.dat ->| Ingert / .ing        |--+
                   +----------------------+  |
                                               v
                   +----------------------+  SQLite  <-> WebView2 UI
table_eng/*.tbl  ->| KuroTools / JSON     |  ^  |
                   +----------------------+  |  +-> DeepL
                                               |
                     revisão ou tradução ------+
                                               |
                         +---------------------+
                         v
              scripts .dat + tabelas .tbl
                         |
                         v
                zzz_ysx_ptbr.p3a
                         |
                         v
             Aplicador C# -> pasta mods
```

## Módulos

- `core.py`: formatos, métricas, extração, round-trip e build.
- `project.py`: SQLite, migração, histórico, backup e estado efetivo.
- `translator.py`: DeepL, glossários, tags, retry e ritmo.
- `web_api.py`: fachada restrita entre frontend e backend.
- `webapp.py`: servidor local autenticado e janela WebView2.
- `frontend/`: interface editorial e dashboards.
- `applicator_src/`: instalador mínimo e reversível.
- `tests/`: comportamento do núcleo, persistência, frontend e provedores.
