# srdesmatamentos


## Aquisição das imagens de sensoriamento remoto
Em utils/scenes.json há os pontos de interesse para o projeto, contendo as respectivas informações sobre as imagens relacionadas. 

Em notebooks/DownloadEarthExplorer.ipynb" utiliza a API do EarthExplorer para verificar quais imagens estão de acordo com as informações do passo anterior.

Executando notebook/EarthExplorer1.0.ipynb será baixado as imagens selecionadas, aplicando web scraping para realizar o download em paralelo.

Com as imagens baixadas, é possível aplicar as máscaras de nuvens. Para isso foi utilizado o notebook/FMask.ipynb


## Geração dos CSVs e snaps
Executando o script main.py será realizado todo o processo de geração dos CSVs (contendo as bandas dos pontos selecionados) e snaps (imagens 20x20 em RGB dos pontos).

A seguir há um resumo de cada script utilizado nesta etapa:
- sentinel2Image: Contém a definição de classe utilizada para representar uma imagem do sentinel-2
- rsdd_enums: Contém os enums utilizados, assim como os paths e índices para as bandas
- processdata: Contém a parte de gerar os primeiros CSVs sem filtros
- snap: Contém as funções para gerar os snaps
- filters: Contém os filtros que são feitos nos CSVs
- utils: Contém funções comuns que são utilizadas pelos outros arquivos


## Classificação com Rede Neural
Em notebook/ann.ipynb encontra-se o script que carrega os dados do RSDD, constrói o modelo de rede neural e realiza a classificação das áreas.

