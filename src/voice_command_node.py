#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json

import numpy as np
import joblib

import rospy
from std_msgs.msg import String

from scipy.sparse import hstack, csr_matrix

try:
    import pyaudio
except ImportError:
    pyaudio = None

try:
    import vosk
except ImportError:
    vosk = None


MODEL_PATH = (
    "/home/est/noetic_workspace/src/husky_target_follower/"
    "voice_control/models/mejor_modelo.joblib"
)

PARAMS_FILE_PATH = (
    "/home/est/noetic_workspace/src/husky_target_follower/"
    "config/operation_mode_parameters.txt"
)

VOSK_MODEL_PATH = (
    "/home/est/noetic_workspace/src/husky_target_follower/"
    "voice_control/models/vosk-model-small-es-0.42"
)

WAKE_WORD = "husky"
STOP_WORDS = ["ejecuta", "ejecute"]

RESPEAKER_RATE = 16000
RESPEAKER_CHANNELS = 6
RESPEAKER_CHANNEL_INDEX = 0
RESPEAKER_WIDTH = 2
CHUNK = 4000

DEFAULT_METODO_POR_INTENTION = {
    "GOAL": 1,
    "PARTIAL": 2,
    "COMPLETE": 3,
    "CYCLIC": 4,
}

SPANISH_NUMBERS = {
    "cero": 0,
    "uno": 1,
    "una": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "once": 11,
    "doce": 12,
    "trece": 13,
    "catorce": 14,
    "quince": 15,
}

MODO_PATTERN = re.compile(
    r"modo(?:\s+de\s+operaci[oó]n)?\s+(\w+)",
    re.IGNORECASE
)


def spanish_word_to_number(word):
    word = word.strip().lower()

    if word in SPANISH_NUMBERS:
        return SPANISH_NUMBERS[word]

    if word.isdigit():
        return int(word)

    return None


def extract_goals_from_text(text):
    """
    Extrae objetivo inicial y objetivo final desde frases como:
    - objetivo inicial uno
    - objetivo final tres
    - del objetivo uno al objetivo tres
    - del uno al tres

    Ignora numeros asociados a 'modo'.
    """

    text = text.lower()

    text = re.sub(
        r"modo(?:\s+de\s+operaci[oó]n)?\s+(cero|uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|\d+)",
        "modo",
        text
    )

    start_goal = 0
    end_goal = 0

    number_pattern = r"(cero|uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|\d+)"

    m_ini = re.search(
        r"objetivo\s+inicial\s+" + number_pattern,
        text
    )

    if m_ini:
        n = spanish_word_to_number(m_ini.group(1))
        if n is not None:
            start_goal = n

    m_fin = re.search(
        r"objetivo\s+final\s+" + number_pattern,
        text
    )

    if m_fin:
        n = spanish_word_to_number(m_fin.group(1))
        if n is not None:
            end_goal = n

    if start_goal == 0 and end_goal == 0:
        m_ruta = re.search(
            r"(?:del|desde)\s+(?:objetivo\s+)?" + number_pattern +
            r"\s+(?:al|hasta)\s+(?:objetivo\s+)?" + number_pattern,
            text
        )

        if m_ruta:
            n1 = spanish_word_to_number(m_ruta.group(1))
            n2 = spanish_word_to_number(m_ruta.group(2))

            if n1 is not None:
                start_goal = n1
            if n2 is not None:
                end_goal = n2

    if start_goal == 0 and end_goal == 0:
        m_single = re.search(
            r"objetivo\s+" + number_pattern,
            text
        )

        if m_single:
            n = spanish_word_to_number(m_single.group(1))
            if n is not None:
                end_goal = n

    return start_goal, end_goal


def clean_command_text(text):
    text = text.lower().strip()

    text = re.sub(rf"\b{WAKE_WORD}\b", "", text)

    for stop_word in STOP_WORDS:
        text = re.sub(rf"\b{stop_word}\b", "", text)

    text = re.sub(r"[,.]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def find_respeaker_device(pa):
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        name = info.get("name", "")

        if "respeaker" in name.lower() or "seeed" in name.lower():
            return i, info

    return None, None


class VoiceCommandNode(object):

    STATE_WAITING_WAKE = "WAITING_WAKE"
    STATE_RECORDING = "RECORDING"

    def __init__(self):
        rospy.init_node("voice_command_node", anonymous=False)
        rospy.loginfo("Iniciando voice_command_node...")

        if pyaudio is None or vosk is None:
            raise RuntimeError(
                "Faltan dependencias. Instala con: "
                "pip install pyaudio vosk"
            )

        if not os.path.isfile(MODEL_PATH):
            raise FileNotFoundError(
                "No se encontro el modelo en {}".format(MODEL_PATH)
            )

        rospy.loginfo("Cargando modelo de IA desde {} ...".format(MODEL_PATH))

        self.model_payload = joblib.load(MODEL_PATH)
        self.tfidf = self.model_payload["tfidf"]
        self.clf = self.model_payload["clf"]
        self.classes = self.model_payload.get("classes", [])

        rospy.loginfo(
            "Modelo cargado: {}".format(
                self.model_payload.get("model_name", "desconocido")
            )
        )

        if not os.path.isdir(VOSK_MODEL_PATH):
            raise FileNotFoundError(
                "No se encontro el modelo de Vosk en {}.".format(VOSK_MODEL_PATH)
            )

        rospy.loginfo("Cargando modelo de reconocimiento de voz Vosk...")
        self.vosk_model = vosk.Model(VOSK_MODEL_PATH)
        self.sample_rate = RESPEAKER_RATE
        self.recognizer = vosk.KaldiRecognizer(
            self.vosk_model,
            self.sample_rate
        )

        self.pa = pyaudio.PyAudio()

        self.device_index, device_info = find_respeaker_device(self.pa)

        if self.device_index is not None:
            rospy.loginfo(
                "ReSpeaker Mic Array detectado: '{}' indice {}".format(
                    device_info.get("name"),
                    self.device_index
                )
            )
            self.channels = RESPEAKER_CHANNELS
            self.channel_index = RESPEAKER_CHANNEL_INDEX
        else:
            rospy.logwarn(
                "No se detecto ReSpeaker. "
                "Usando microfono por defecto del sistema."
            )
            self.device_index = None
            self.channels = 1
            self.channel_index = 0

        self.stream = self.pa.open(
            rate=self.sample_rate,
            format=pyaudio.paInt16,
            channels=self.channels,
            input=True,
            input_device_index=self.device_index,
            frames_per_buffer=CHUNK,
        )

        self.result_pub = rospy.Publisher(
            "/voice_command/parsed_command",
            String,
            queue_size=10
        )

        self.state = self.STATE_WAITING_WAKE
        self._running = True

        rospy.on_shutdown(self.shutdown)

        rospy.loginfo(
            "voice_command_node listo. "
            "Esperando palabra de activacion 'husky'..."
        )

    def get_audio_chunk(self):
        raw = self.stream.read(CHUNK, exception_on_overflow=False)

        if self.channels == 1:
            return raw

        audio_np = np.frombuffer(raw, dtype=np.int16)

        usable = (len(audio_np) // self.channels) * self.channels
        audio_np = audio_np[:usable].reshape(-1, self.channels)

        mono = audio_np[:, self.channel_index]

        return mono.tobytes()

    def __init__(self):
        rospy.init_node("voice_command_node", anonymous=False)
        rospy.loginfo("Iniciando voice_command_node...")

        if pyaudio is None or vosk is None:
            raise RuntimeError(
                "Faltan dependencias. Instala con: "
                "pip install pyaudio vosk"
            )

        if not os.path.isfile(MODEL_PATH):
            raise FileNotFoundError(
                "No se encontro el modelo en {}".format(MODEL_PATH)
            )

        rospy.loginfo("Cargando modelo de IA desde {} ...".format(MODEL_PATH))

        self.model_payload = joblib.load(MODEL_PATH)
        self.tfidf = self.model_payload["tfidf"]
        self.clf = self.model_payload["clf"]
        self.classes = self.model_payload.get("classes", [])

        rospy.loginfo(
            "Modelo cargado: {}".format(
                self.model_payload.get("model_name", "desconocido")
            )
        )

        if not os.path.isdir(VOSK_MODEL_PATH):
            raise FileNotFoundError(
                "No se encontro el modelo de Vosk en {}.".format(VOSK_MODEL_PATH)
            )

        rospy.loginfo("Cargando modelo de reconocimiento de voz Vosk...")
        self.vosk_model = vosk.Model(VOSK_MODEL_PATH)
        self.sample_rate = RESPEAKER_RATE
        self.recognizer = vosk.KaldiRecognizer(
            self.vosk_model,
            self.sample_rate
        )

        self.pa = pyaudio.PyAudio()

        self.device_index, device_info = find_respeaker_device(self.pa)

        if self.device_index is not None:
            rospy.loginfo(
                "ReSpeaker Mic Array detectado: '{}' indice {}".format(
                    device_info.get("name"),
                    self.device_index
                )
            )
            self.channels = RESPEAKER_CHANNELS
            self.channel_index = RESPEAKER_CHANNEL_INDEX
        else:
            rospy.logwarn(
                "No se detecto ReSpeaker. "
                "Usando microfono por defecto del sistema."
            )
            self.device_index = None
            self.channels = 1
            self.channel_index = 0

        self.stream = self.pa.open(
            rate=self.sample_rate,
            format=pyaudio.paInt16,
            channels=self.channels,
            input=True,
            input_device_index=self.device_index,
            frames_per_buffer=CHUNK,
        )

        self.result_pub = rospy.Publisher(
            "/voice_command/parsed_command",
            String,
            queue_size=10
        )

        self.state = self.STATE_WAITING_WAKE
        self._running = True
        self.command_buffer = ""   # NUEVO: acumula texto finalizado durante la grabación

        rospy.on_shutdown(self.shutdown)

        rospy.loginfo(
            "voice_command_node listo. "
            "Esperando palabra de activacion 'husky'..."
        )

    def listen_loop(self):
    
        while self._running and not rospy.is_shutdown():

            try:
                data = self.get_audio_chunk()
            except Exception as e:
                rospy.logerr("Error leyendo audio: {}".format(e))
                rospy.sleep(0.1)
                continue

            is_final_segment = self.recognizer.AcceptWaveform(data)

            # Texto del segmento que Vosk acaba de cerrar (si lo cerró)
            final_segment_text = ""
            if is_final_segment:
                final_result = json.loads(self.recognizer.Result())
                final_segment_text = final_result.get("text", "").lower()

                if final_segment_text:
                    rospy.loginfo("VOSK (final): {}".format(final_segment_text))

            partial = json.loads(self.recognizer.PartialResult())
            partial_text = partial.get("partial", "").lower()

            if partial_text:
                rospy.loginfo("VOSK: {}".format(partial_text))

            if self.state == self.STATE_WAITING_WAKE:

                wake_detected = (
                    re.search(rf"\b{WAKE_WORD}\b", partial_text)
                    or re.search(rf"\b{WAKE_WORD}\b", final_segment_text)
                )

                if wake_detected:
                    rospy.loginfo(
                        "Palabra de activacion 'husky' detectada. "
                        "Grabando comando..."
                    )

                    self.state = self.STATE_RECORDING
                    self.command_buffer = ""
                    self.recognizer = vosk.KaldiRecognizer(
                        self.vosk_model,
                        self.sample_rate
                    )

            elif self.state == self.STATE_RECORDING:

                # Acumulamos cada segmento que Vosk va cerrando, para no
                # perder palabras dichas antes de un corte interno.
                if final_segment_text:
                    self.command_buffer = (
                        self.command_buffer + " " + final_segment_text
                    ).strip()

                stop_in_partial = any(
                    re.search(rf"\b{w}\b", partial_text)
                    for w in STOP_WORDS
                )
                stop_in_final = any(
                    re.search(rf"\b{w}\b", final_segment_text)
                    for w in STOP_WORDS
                )
                stop_in_buffer = any(
                    re.search(rf"\b{w}\b", self.command_buffer)
                    for w in STOP_WORDS
                )


                if stop_in_partial or stop_in_final or stop_in_buffer:
                    final = json.loads(self.recognizer.FinalResult())
                    rospy.loginfo("FINAL: {}".format(final))

                    final_text = final.get("text", "").lower()
                    if final_text:
                        self.command_buffer = (
                            self.command_buffer + " " + final_text
                        ).strip()

                    full_text = self.command_buffer or partial_text

                    rospy.loginfo(
                        "Comando completo recibido: '{}'".format(full_text)
                    )

                    try:
                        self.handle_command(full_text)
                    except Exception as e:
                        rospy.logerr("Fallo procesando comando, se ignora y se sigue escuchando: {}".format(e))

                    self.state = self.STATE_WAITING_WAKE
                    self.command_buffer = ""
                    self.recognizer = vosk.KaldiRecognizer(
                        self.vosk_model,
                        self.sample_rate
                    )

                    rospy.loginfo(
                        "Esperando palabra de activacion 'husky'..."
                    )

    def predict_intention_and_goals(self, command_text):
        """
        Predice la intencion usando el modelo entrenado.
        Los objetivos se extraen del texto para formar las features numericas.
        """

        try:
            start_goal, end_goal = extract_goals_from_text(command_text)

            T = self.tfidf.transform([command_text])
            N = csr_matrix(
                np.array([[start_goal, end_goal]], dtype=float)
            )

            X = hstack([T, N])

            intention = self.clf.predict(X)[0]

        except Exception as e:
            rospy.logerr("Error al predecir con el modelo de IA: {}".format(e))
            raise

        intention = str(intention).strip().upper()
        start_goal = int(start_goal)
        end_goal = int(end_goal)

        return intention, start_goal, end_goal

    def extract_metodo_operacion(self, command_text, intention):
        match = MODO_PATTERN.search(command_text)

        if match:
            numero = spanish_word_to_number(match.group(1))

            if numero is not None:
                return numero

        metodo = DEFAULT_METODO_POR_INTENTION.get(intention, 0)

        rospy.logwarn(
            "El comando no menciona el modo explicitamente. "
            "Se usa valor por defecto para intencion='{}': {}".format(
                intention,
                metodo
            )
        )

        return metodo

    def write_parameters_file(self, metodo, objetivo_inicial, objetivo_final):
        content = (
            "Parametros de control para el modo de operacion\n"
            "\n"
            "Metodo de operacion:{}\n"
            "\n"
            "Objetivos para definir trayectoria\n"
            "\n"
            "Objetivo inicial:{}\n"
            "Objetivo final:{}\n"
        ).format(
            metodo,
            objetivo_inicial,
            objetivo_final
        )

        os.makedirs(os.path.dirname(PARAMS_FILE_PATH), exist_ok=True)

        with open(PARAMS_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(content)

        rospy.loginfo(
            "Archivo de parametros actualizado en {}".format(PARAMS_FILE_PATH)
        )

    def handle_command(self, raw_text):
        command_text = clean_command_text(raw_text)

        if not command_text:
            rospy.logwarn(
                "No se pudo extraer texto de comando valido. Se ignora."
            )
            return

        try:
            intention, start_goal, end_goal = self.predict_intention_and_goals(
                command_text
            )
        except Exception:
            rospy.logerr(
                "No se pudo interpretar el comando con el modelo de IA."
            )
            return

        metodo = self.extract_metodo_operacion(command_text, intention)

        rospy.loginfo(
            "Interpretado -> intencion: {}, metodo: {}, "
            "objetivo_inicial: {}, objetivo_final: {}".format(
                intention,
                metodo,
                start_goal,
                end_goal
            )
        )

        self.write_parameters_file(
            metodo,
            start_goal,
            end_goal
        )

        result_msg = String()

        result_msg.data = json.dumps({
            "command_text": command_text,
            "intention": intention,
            "metodo_operacion": metodo,
            "objetivo_inicial": start_goal,
            "objetivo_final": end_goal,
        })

        self.result_pub.publish(result_msg)

    def shutdown(self):
        rospy.loginfo("Cerrando voice_command_node...")
        self._running = False

        try:
            self.stream.stop_stream()
            self.stream.close()
            self.pa.terminate()
        except Exception:
            pass


def main():
    try:
        node = VoiceCommandNode()
        node.listen_loop()

    except rospy.ROSInterruptException:
        pass

    except Exception as e:
        rospy.logerr("voice_command_node fallo: {}".format(e))
        raise


if __name__ == "__main__":
    main()
