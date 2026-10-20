# Controle Corporal eFootball

Aplicacao experimental em Python que usa a webcam e o MediaPipe Pose Landmarker
para reconhecer a inclinacao do tronco e, quando ativado, enviar as setas
esquerda/direita ao computador com `pydirectinput`.

> **Aviso:** a comunicacao com o eFootball nao e garantida. O jogo pode ignorar
> teclas sintetizadas, exigir um comando ou dispositivo diferente, ou restringir
> automacao. Este projeto nao injeta codigo no jogo nem confirma que uma entrada
> foi recebida. Use por sua conta e risco e respeite os termos aplicaveis.

## Requisitos

- Windows recomendado (o controlo de foco e teclado foi implementado para
  Windows).
- Python e as dependencias listadas em `requirements.txt`. O ambiente usado para
  validar este projeto e Python 3.14.4.
- Webcam acessivel pelo sistema.
- Ficheiro do modelo MediaPipe Pose Landmarker Lite, obtido separadamente.

## Instalacao

No PowerShell, na pasta do projeto:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Descarregue o modelo
[pose_landmarker_lite.task](https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task)
e guarde-o neste caminho:

```text
%LOCALAPPDATA%\BodyMotionControl\models\pose_landmarker_lite.task
```

O ficheiro do modelo nao e incluido no repositorio. Para usar outro ficheiro
`.task` compativel, defina `MEDIAPIPE_POSE_MODEL` para o caminho completo:

```powershell
$env:MEDIAPIPE_POSE_MODEL = "C:\caminho\para\pose_landmarker_lite.task"
```

## Execucao

```powershell
.\.venv\Scripts\python.exe .\main.py
```

Permita o acesso do Python a webcam nas definicoes de privacidade do Windows.
O programa mostra o esqueleto e o angulo reconhecido na janela da camera.

## Controlos

- **C**: ativa ou desativa o envio de teclado, com a janela da camera em foco.
- **X**: parada de emergencia; desativa o controlo e liberta a seta pressionada.
- **ESC**: encerra o programa.
- Inclinar o tronco para a esquerda ou direita envia a tecla correspondente
  enquanto o gesto estiver ativo. As teclas podem ser alteradas em
  `KEY_MAPPING`, em `main.py`.

O controlo inicia desativado e tambem e desativado quando a janela da camera
perde o foco. Os limiares de entrada/saida, a suavizacao e o intervalo entre
ativacoes ajudam a reduzir mudancas causadas por oscilacoes da deteccao. Teste
primeiro os gestos com o controlo desativado e confirme os comandos configurados
no proprio eFootball antes de o ativar.

## Testes simulados

Os testes nao abrem a webcam nem enviam teclas reais:

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_main
```
