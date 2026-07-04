# DATASET.md

## Nombre del conjunto de datos

Conjunto de comandos de voz etiquetados para la selección automática del modo de operación del robot Husky A200.

## Propósito del conjunto de datos

El conjunto de datos fue construido para entrenar y evaluar modelos de clasificación supervisada capaces de interpretar comandos de voz en lenguaje natural. Cada comando representa una instrucción que un usuario podría emitir para controlar el modo de operación de un robot móvil Husky A200.

El objetivo principal del conjunto de datos es permitir que el sistema identifique automáticamente la intención del usuario y extraiga los objetivos de navegación necesarios para generar el archivo de parámetros utilizado por el robot.

## Estructura de los archivos

Los datos se dividen en dos archivos principales:

```text
data/train_commands.csv
data/test_commands.csv
```

El archivo `train_commands.csv` se utiliza para el entrenamiento de los modelos de clasificación. El archivo `test_commands.csv` se utiliza únicamente para la evaluación final de los modelos, por lo que no debe emplearse durante el entrenamiento.

## Cantidad de muestras

El conjunto de datos utilizado en el proyecto se organizó de la siguiente manera:

| Subconjunto | Cantidad de comandos | Uso |
|---|---:|---|
| Entrenamiento | 607 | Ajuste de los modelos de clasificación |
| Prueba | 153 | Evaluación del desempeño final |
| Total | 760 | Conjunto completo de comandos etiquetados |

## Formato de las muestras

Cada muestra contiene cuatro atributos principales:

| Columna | Descripción |
|---|---|
| `command` | Texto completo del comando de voz. |
| `intent` | Intención o clase asociada al comando. |
| `initial_goal` | Objetivo inicial mencionado en el comando. |
| `final_goal` | Objetivo final mencionado en el comando. |

Ejemplo de formato:

```csv
command,intent,initial_goal,final_goal
"ir al objetivo 5",GOAL,0,5
"recorrer del objetivo 2 al objetivo 6",PARTIAL,2,6
"realizar la trayectoria completa",COMPLETE,0,0
"activar recorrido ciclico",CYCLIC,0,0
```

## Clases utilizadas

El problema se formuló como una clasificación multiclase. Las clases corresponden a los modos de operación disponibles en el sistema de navegación del robot:

| Clase | Significado |
|---|---|
| `GOAL` | Desplazamiento hacia un objetivo específico. |
| `PARTIAL` | Seguimiento de una trayectoria parcial entre un objetivo inicial y uno final. |
| `COMPLETE` | Recorrido completo de todos los objetivos registrados. |
| `CYCLIC` | Recorrido cíclico de la trayectoria. |

## Recolección de los datos

Los comandos fueron construidos a partir de frases que representan instrucciones realistas que un usuario podría pronunciar durante la operación del robot. Para evitar que el modelo memorizara únicamente frases específicas, se incorporaron diferentes formas de expresar una misma acción.

Entre las variaciones consideradas se incluyeron:

- Comandos directos, por ejemplo: `ir al objetivo 4`.
- Comandos con lenguaje más natural, por ejemplo: `quiero que el robot vaya al objetivo 4`.
- Comandos para recorridos parciales, por ejemplo: `realizar la trayectoria del objetivo 2 al objetivo 6`.
- Comandos para recorridos completos, por ejemplo: `ejecutar todo el recorrido`.
- Comandos para recorridos cíclicos, por ejemplo: `repetir la trayectoria de forma cíclica`.
- Diferentes números de objetivos para representar múltiples escenarios de navegación.

## Proceso de etiquetado

Cada comando fue etiquetado manualmente de acuerdo con la intención que representa. El proceso de etiquetado consistió en asignar:

1. La clase correspondiente al modo de operación.
2. El objetivo inicial, cuando aplica.
3. El objetivo final, cuando aplica.

Para los comandos de tipo `GOAL`, el objetivo inicial se asigna como `0` y el objetivo final corresponde al objetivo solicitado por el usuario. Para los comandos `PARTIAL`, se asignan tanto el objetivo inicial como el objetivo final. Para los comandos `COMPLETE` y `CYCLIC`, ambos objetivos se registran como `0`, ya que estos modos no requieren seleccionar un intervalo específico.

## Criterios de calidad

Durante la elaboración del conjunto de datos se buscó mantener consistencia en los siguientes aspectos:

- Que cada comando tuviera una única intención principal.
- Que los objetivos fueran coherentes con el tipo de comando.
- Que no existieran etiquetas contradictorias.
- Que las clases estuvieran representadas mediante distintas formas de lenguaje.
- Que los comandos de prueba no fueran utilizados durante el entrenamiento.

## Limitaciones del conjunto de datos

El conjunto de datos presenta algunas limitaciones importantes:

- Los comandos fueron diseñados para el contexto específico del robot Husky A200 y sus cuatro modos de operación.
- El sistema no está pensado para interpretar conversaciones abiertas.
- Las frases se encuentran orientadas al idioma español.
- El desempeño puede disminuir si el reconocimiento de voz transcribe incorrectamente el comando.
- El conjunto de datos no cubre todas las posibles formas reales en que una persona podría hablar.
- La extracción de objetivos depende de que los números sean reconocidos correctamente por el sistema de voz.
- No se evalúan variaciones fuertes de acento, ruido ambiental extremo o micrófonos de baja calidad.

## Consideraciones sobre ruido, audio y ambiente

A diferencia de un proyecto de clasificación de imágenes, este conjunto de datos no depende de variaciones de iluminación, cámara, fondos u oclusión visual. Sin embargo, sí puede verse afectado por condiciones acústicas, tales como:

- Ruido ambiental.
- Eco en la habitación.
- Distancia entre el usuario y el micrófono.
- Calidad del micrófono.
- Claridad de pronunciación.
- Errores del motor de reconocimiento de voz.

Estas condiciones deben considerarse al interpretar el desempeño experimental del sistema.

## Uso recomendado

Este conjunto de datos debe utilizarse para:

- Entrenar modelos de clasificación supervisada de comandos de voz.
- Comparar algoritmos de clasificación de texto.
- Evaluar la selección automática de modos de operación en el robot Husky A200.
- Validar la integración entre reconocimiento de voz, procesamiento de texto y navegación robótica.

## Uso no recomendado

Este conjunto de datos no debe utilizarse para:

- Sistemas de conversación general.
- Reconocimiento automático de voz desde audio crudo.
- Clasificación de comandos fuera del dominio de navegación del Husky A200.
- Aplicaciones críticas de seguridad sin validación adicional.
- Sistemas en producción sin ampliar el conjunto de datos y realizar pruebas con más usuarios.
