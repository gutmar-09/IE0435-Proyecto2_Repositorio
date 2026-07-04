# Clasificación de comandos de voz para el robot Husky A200

Este repositorio contiene los archivos principales del Proyecto 2 del curso IE0435 - Inteligencia Artificial Aplicada a la Ingeniería Eléctrica. El proyecto desarrolla un sistema de clasificación supervisada capaz de interpretar comandos de voz para automatizar la selección del modo de operación de un robot móvil Husky A200 simulado en Gazebo con ROS Noetic sobre Ubuntu 20.04.6 LTS.

El sistema permite que el usuario indique por voz el modo de operación deseado, el objetivo inicial y el objetivo final. Posteriormente, el comando reconocido se transforma en texto, se procesa mediante un modelo de aprendizaje automático previamente entrenado y se genera automáticamente el archivo `operation_mode_parameters.txt`, utilizado por el sistema de navegación del robot.

## Estructura del repositorio

```text
voice_control/
├── README.md
├── DATASET.md
├── LICENSE
├── requirements.txt
├── environment.yml
├── data/
│   ├── train_commands.csv
│   └── test_commands.csv
├── models/
│   └── mejor_modelo.joblib
├── src/
│   ├── train_voice_command_models.py
│   └── voice_command_node.py
├── reports/
│   └── IE0435_Reporte_Modelos.pdf
├── video/
│   └── demo.mp4
└── docs/
    └── repository_notes.md
```

## Descripción general del sistema

El proyecto se divide en dos programas principales:

1. `train_voice_command_models.py`: programa encargado de cargar los conjuntos de entrenamiento y prueba, transformar los comandos mediante TF-IDF, entrenar diferentes modelos de clasificación supervisada y seleccionar automáticamente el modelo con mejor F1-score ponderado.

2. `voice_command_node.py`: nodo de ROS encargado de capturar audio desde el micrófono, convertir el habla a texto con Vosk, limpiar el comando reconocido, extraer los objetivos mencionados por el usuario, clasificar la intención mediante el modelo entrenado y generar el archivo de parámetros requerido por el robot.

Los modelos evaluados fueron:

- Árbol de Decisión.
- Naive Bayes.
- K-Nearest Neighbors.
- SVM lineal.
- SVM con kernel RBF.

El modelo definitivo seleccionado fue SVM con kernel RBF, debido a que obtuvo el mejor desempeño general en el conjunto de prueba.

## Requisitos del sistema

El repositorio fue preparado para ejecutarse en:

- Ubuntu 20.04.6 LTS.
- ROS Noetic.
- Python 3.8 o superior.
- Gazebo compatible con ROS Noetic.
- Micrófono funcional.
- Modelo de reconocimiento de voz Vosk en español.

## Preparación de los datos

Los archivos de datos deben ubicarse dentro de la carpeta `data/`:

```text
data/train_commands.csv
data/test_commands.csv
```

Cada archivo debe contener, como mínimo, las siguientes columnas:

```text
command,intent,initial_goal,final_goal
```

Donde:

- `command`: texto completo del comando de voz.
- `intent`: clase o intención del comando.
- `initial_goal`: objetivo inicial detectado o asignado.
- `final_goal`: objetivo final detectado o asignado.

Las clases utilizadas por el sistema son:

- `GOAL`: desplazamiento hacia un objetivo específico.
- `PARTIAL`: recorrido parcial entre dos objetivos.
- `COMPLETE`: recorrido completo de la trayectoria registrada.
- `CYCLIC`: recorrido cíclico.

El programa debe realizar las siguientes etapas:

1. Cargar los comandos de entrenamiento y prueba.
2. Convertir los comandos a representación numérica mediante TF-IDF.
3. Entrenar los modelos definidos.
4. Evaluar cada modelo con Accuracy, Precision, Recall y F1-score.
5. Seleccionar el modelo con mayor F1-score ponderado.
6. Guardar el modelo seleccionado en `models/mejor_modelo.joblib`.

El nodo permanecerá esperando la palabra de activación `Husky`. Después de detectarla, almacenará el comando hasta escuchar una palabra de finalización como `ejecuta` o `ejecute`.

Ejemplos de comandos válidos:

```text
Husky ir al objetivo 5 ejecuta
Husky realiza la trayectoria del objetivo 2 al objetivo 6 ejecuta
Husky completa todo el recorrido ejecute
Husky activa el recorrido cíclico ejecuta
```

## Salida esperada

El sistema debe generar o actualizar el archivo:

```text
operation_mode_parameters.txt
```

Este archivo contiene la información requerida por el sistema de navegación:

```text
modo_operacion objetivo_inicial objetivo_final
```

## Reporte final

El informe final del proyecto se encuentra en:

```text
reports/IE0435_Reporte_Modelos.pdf
```

## Video demostrativo

El video del funcionamiento completo del sistema debe colocarse dentro de la carpeta:

```text
video/
```

## Consideración si se desea replicar el proyecto

Para lograr reproducir este proyecto se deben realizar muchas instalaciones, como lo es el caso de ROS Noetic, Vosk y varias bibliotecas. Es por este motivo que en este repertorio se explica el funcionamiento del proyecto de forma descriptiva y explicativa.

## Autor

Marlon Gutiérrez Vásquez  
Carné: C33619  
Universidad de Costa Rica  
IE0435 - Inteligencia Artificial Aplicada a la Ingeniería Eléctrica  
I ciclo 2026
