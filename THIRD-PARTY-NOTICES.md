# Avisos de terceiros

## django-observatory

A camada de apresentação veio do django-observatory, por meio do WMS-Almoxarifado (repositório
`joaorighetto/WMS-Almoxarifado`, commit `70798439575da9d51547b0bc585b6a783b2e524c`). Com a
interface Clean, o CSS, os tokens e o `shell.js` com tema foram reescritos; o que ainda é
copiado de lá é a paginação (`interface/templates/interface/_paginacao.html`) e as template
tags `querystring_pagina`, `intervalo_paginas`, `separador_milhar` e `quantidade`
(`interface/templatetags/interface_extras.py`).

- Projeto: https://github.com/AzeemQidwai/django-observatory
- Versão: 0.1.0 (PyPI)
- Commit: 6edda16667c8a8601670f76e3286f86bed16e37d
- Arquivos de origem: `django_observatory/static/django_observatory/app.css`,
  `django_observatory/static/django_observatory/app.js`,
  `django_observatory/templates/django_observatory/base.html`

Texto da licença (reproduzido do arquivo `LICENSE` do commit acima):

```text
MIT License

Copyright (c) 2026 django-observability contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Fontes (SIL Open Font License 1.1)

Os arquivos `.woff2` em `interface/static/interface/fonts/` (subconjunto latino) vêm dos pacotes
`@fontsource/geist-sans@5.3.0`, `@fontsource/geist-mono@5.3.0` e `@fontsource/dm-sans@5.3.0`
(jsDelivr) e são distribuídos sob a SIL Open Font License 1.1. O texto de cada licença, com o
aviso de copyright, fica ao lado das fontes:

- Geist e Geist Mono (Vercel, em colaboração com basement.studio):
  `interface/static/interface/fonts/OFL-Geist.txt` e `OFL-GeistMono.txt`;
- DM Sans (Colophon Foundry / Google, The DM Sans Project Authors):
  `interface/static/interface/fonts/OFL-DMSans.txt`.

## Lucide

Os traços dos ícones em `interface/templates/interface/_icone.html` vêm do Lucide
(https://lucide.dev), sob a licença ISC:

```text
ISC License

Copyright (c) for portions of Lucide are held by Cole Bemis 2013-2022 as part of Feather (MIT).
All other copyright (c) for Lucide are held by Lucide Contributors 2022.

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
```

## htmx

`interface/static/interface/vendor/htmx/htmx-4.0.0.min.js` é o htmx 4.0.0, distribuído sob a
licença em `interface/static/interface/vendor/htmx/LICENSE`.
