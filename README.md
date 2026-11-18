BaixadorYT (projeto aberto em Python)
Aplicativo simples com interface gráfica para Windows. É um ponto de partida para você aprender e adicionar funções.
Funções
- Vídeo em MP4 (quando o formato estiver disponível), até 4K; resolução depende do vídeo de origem
- Áudio MP3 e M4A
- Playlist completa (opcional)
- Legendas em português/inglês, inclusive automáticas quando disponíveis; o arquivo pode ser SRT, VTT ou outro formato ofertado pela plataforma
- Salvar miniatura e informações do vídeo (.info.json)
- Acompanhar progresso, cancelar e selecionar a pasta
Instalação no Windows 10/11
1. Instale o Python 3.11 ou mais recente, marcando a opção para adicionar ao PATH.
2. Abra o PowerShell e execute (uma linha de cada vez):
winget install --id Gyan.FFmpeg -e
winget install --id DenoLand.Deno -e
py -m pip install --upgrade "yt-dlp[default]"
ffmpeg/`ffprobe` são usados para juntar áudio e vídeo e converter MP3. O Deno é recomendado para melhorar a compatibilidade do yt-dlp com o YouTube. Feche e reabra o PowerShell após as instalações.
3. Dê dois cliques em iniciar_windows.bat, na pasta do projeto. Ele verifica/atualiza o yt-dlp pela internet e abre a interface.
Alternativa no terminal:
py baixador_yt.py
Se o winget não estiver disponível, instale o FFmpeg pela página https://ffmpeg.org/download.html e Deno por https://docs.deno.com/runtime/getting_started/installation/ . Certifique-se de que ffmpeg e ffprobe sejam reconhecidos no PATH. Alternativamente, ponha os dois executáveis em uma pasta bin ao lado do arquivo Python.
Como usar
1. Cole o link de vídeo ou playlist.
2. Escolha vídeo, áudio ou somente legendas.
3. Se necessário, marque "Baixar playlist inteira".
4. Escolha pasta, qualidade e opções adicionais.
5. Clique em "Iniciar download".
Gerar um .exe no próprio Windows
Execute gerar_exe_windows.bat. Ele usa PyInstaller; o resultado deve aparecer em dist\BaixadorYT.exe. O EXE ainda pode depender de FFmpeg e Deno instalados. Teste-o em um computador Windows antes de distribuir. O executável não foi gerado nem testado neste ambiente.
Solução de problemas
- Se um download falhar, atualize: py -m pip install -U "yt-dlp[default]".
- Se o app disser que não há FFmpeg, feche e reabra o programa após instalar o pacote e confira ffmpeg -version e ffprobe -version.
- Se o YouTube apresentar erro de formato, acesso ou verificação, ele pode ter mudado. O aplicativo não contorna DRM nem restrições de acesso.
- A barra acompanha o arquivo atual, não a playlist inteira.
- O botão cancelar atua no próximo evento de progresso; em alguns casos pode levar um pouco para interromper a operação.
Estrutura do projeto
- baixador_yt.py — interface + lógica de download
- iniciar_windows.bat — prepara dependência Python e executa
- gerar_exe_windows.bat — cria executável com PyInstaller
- requirements.txt — dependência principal
Respeite os direitos autorais e os termos das plataformas. Baixe apenas materiais cuja obtenção seja expressamente permitida ou autorizada.
