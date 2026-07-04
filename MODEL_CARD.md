# MODEL_CARD.md


**Nombre del modelo:** Clasificador de comandos de voz para robot Husky A200  
**Versión:** v5.0  
**Archivo del modelo:** `models/mejor_modelo.joblib`  
**Modelo seleccionado:** SVM con kernel RBF  
**Representación de entrada:** TF-IDF  

## Descripción general

Este modelo fue desarrollado para clasificar comandos de voz convertidos previamente a texto. Su función principal es identificar la intención del usuario y permitir la selección automática del modo de operación de un robot móvil Husky A200 simulado en Gazebo utilizando ROS Noetic.

El modelo no trabaja directamente con la señal de audio. Primero, el motor Vosk convierte el comando hablado en texto. Posteriormente, el texto se limpia, se transforma mediante TF-IDF y se clasifica mediante el modelo entrenado.

## Intended use

El modelo está diseñado para utilizarse en un sistema de navegación robótica donde el usuario puede controlar el modo de operación del robot mediante comandos de voz en español.

Usos previstos:

- Identificar comandos para ir a un objetivo específico.
- Identificar comandos para ejecutar una trayectoria parcial.
- Identificar comandos para ejecutar una trayectoria completa.
- Identificar comandos para ejecutar un recorrido cíclico.
- Integrarse con un nodo de ROS para generar automáticamente archivos de parámetros.
- Apoyar pruebas académicas de clasificación supervisada aplicada a robótica móvil.

## Out-of-scope

El modelo no está diseñado para:

- Mantener conversaciones abiertas con el usuario.
- Interpretar instrucciones fuera del dominio de navegación definido.
- Clasificar audio directamente.
- Sustituir un sistema formal de seguridad robótica.
- Operar en ambientes reales sin validación adicional.
- Tomar decisiones críticas sin supervisión humana.
- Interpretar comandos ambiguos o contradictorios.

## Data summary

El modelo fue entrenado utilizando comandos de voz representados como texto. El conjunto de datos contiene frases en español que simulan instrucciones reales para controlar el robot.

Cantidad de muestras utilizadas:

| Subconjunto | Cantidad |
|---|---:|
| Entrenamiento | 607 comandos |
| Prueba | 153 comandos |
| Total | 760 comandos |

Cada muestra contiene:

- Texto completo del comando.
- Intención asociada.
- Objetivo inicial.
- Objetivo final.

Las clases utilizadas fueron:

- `GOAL`.
- `PARTIAL`.
- `COMPLETE`.
- `CYCLIC`.

### Variaciones consideradas

El conjunto de datos incluye diferentes formas de expresar una misma intención. Por ejemplo, una instrucción para ir a un objetivo puede aparecer como:

- `ir al objetivo 5`.
- `dirigirse al objetivo 5`.
- `quiero que el robot vaya al objetivo 5`.

En este proyecto no aplican variaciones de iluminación, cámara o fondo, porque no se trabaja con imágenes. En su lugar, las variaciones relevantes corresponden a:

- Diferentes estructuras gramaticales.
- Diferentes palabras para una misma intención.
- Diferentes números de objetivo.
- Comandos cortos y comandos más naturales.

## Labeling process

El etiquetado se realizó de forma manual. Cada comando fue revisado y asociado con una de las cuatro clases disponibles. Además, se asignaron los valores correspondientes de objetivo inicial y objetivo final.

Criterios de etiquetado:

- Si el comando solicita ir a un único objetivo, se etiqueta como `GOAL`.
- Si el comando solicita ir de un objetivo inicial a uno final, se etiqueta como `PARTIAL`.
- Si el comando solicita ejecutar toda la trayectoria, se etiqueta como `COMPLETE`.
- Si el comando solicita repetir o ejecutar la trayectoria de forma cíclica, se etiqueta como `CYCLIC`.

Para mantener consistencia, los comandos `COMPLETE` y `CYCLIC` utilizan `0` como objetivo inicial y `0` como objetivo final, debido a que estos modos no requieren un intervalo específico de objetivos.

## Metrics

Los modelos fueron evaluados con las siguientes métricas:

- Accuracy.
- Precision ponderada.
- Recall ponderado.
- F1-score ponderado.

El criterio principal de selección fue el F1-score ponderado, debido a que esta métrica combina Precision y Recall y permite comparar el desempeño general de cada clasificador.

## Evaluation split

La evaluación se realizó utilizando un conjunto de prueba independiente de 153 comandos, el cual no fue utilizado durante el entrenamiento.

| Modelo | Accuracy | Precision | Recall | F1-score |
|---|---:|---:|---:|---:|
| SVM RBF | 0.9673 | 0.9677 | 0.9673 | 0.9674 |
| SVM Lineal | 0.9608 | 0.9619 | 0.9608 | 0.9608 |
| Naive Bayes | 0.9477 | 0.9464 | 0.9477 | 0.9463 |
| Árbol de Decisión | 0.9346 | 0.9421 | 0.9346 | 0.9340 |
| KNN, k = 5 | 0.9216 | 0.9248 | 0.9216 | 0.9214 |

El modelo SVM con kernel RBF fue seleccionado como modelo definitivo debido a que obtuvo el mejor F1-score ponderado.

## Ethical and safety notes

Aunque el sistema fue desarrollado con fines académicos, existen consideraciones importantes:

- Un error de clasificación podría generar un modo de operación distinto al solicitado por el usuario.
- El sistema depende de la calidad de la transcripción generada por Vosk.
- Ruido ambiental, mala pronunciación o micrófonos defectuosos pueden afectar la interpretación del comando.
- El sistema debe utilizarse con supervisión si se conecta a un robot físico.
- No debe emplearse como único mecanismo de seguridad en navegación real.
- Es recomendable implementar confirmación visual o verbal antes de ejecutar movimientos críticos.

Se pueden existir sesgos asociados a:

- Acentos específicos.
- Formas particulares de hablar.
- Frases similares a las utilizadas durante el entrenamiento.
- Ambientes acústicos controlados.

## Limitations

Limitaciones principales del modelo:

- Solo reconoce las clases definidas durante el entrenamiento.
- No interpreta instrucciones fuera del dominio del proyecto.
- Puede fallar si el texto transcrito por Vosk contiene errores importantes.
- No detecta intención si el comando no se parece a las frases del conjunto de datos.
- La extracción de objetivos depende de reglas adicionales mediante expresiones regulares.
- No fue entrenado con una gran cantidad de usuarios reales.
- No fue validado en ambientes con ruido extremo.


## Reproducibility

### Sistema operativo

- Ubuntu 20.04.6 LTS.

### Software principal

- Python 3.8 o superior.
- ROS Noetic.
- Gazebo.
- Vosk.
- scikit-learn.
- pandas.
- numpy.
- joblib.

### Hardware usado

- Computadora personal con Ubuntu 20.04.6 LTS.
- Micrófono integrado o externo.
- Robot Husky A200 simulado en Gazebo.
