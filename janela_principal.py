# -*- coding: utf-8 -*-

import sys
import re
import os
import json
import xml.etree.ElementTree as ET
import json as _json_aux
import urllib.request
import urllib.parse
import html as _html
from html.parser import HTMLParser

try:
    import psycopg2
except ImportError:
    psycopg2 = None

from PySide6.QtGui import QColor, QAction
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRunnable, QThreadPool, QObject, Signal
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QLineEdit,
    QCheckBox,
    QMenu,
    QHeaderView,
    QFormLayout,
    QGroupBox,
)

from leitor_xml import LeitorXML
from baixador_xml import baixar_xml_do_pdf


# ============================================================
# CONFIGURAÇÃO DE ACESSO
# ============================================================

# ------------------------------------------------------------
# SENHA PARA ENTRAR NA CONFIGURAÇÃO DO BANCO
# ------------------------------------------------------------
#
# Você pode trocar diretamente aqui.
#
# Ou definir uma variável de ambiente:
#
# Windows:
# set XML_APP_PASSWORD=123456
#
# ------------------------------------------------------------

SENHA_ACESSO = os.getenv(
    "XML_APP_PASSWORD",
    "1234"
)


# ============================================================
# CAMPO ANIMADO
# ============================================================

# Ordem visual padrão das 18 colunas.
# Os índices são os índices lógicos usados pela tabela e pelas rotinas internas.
ORDEM_PADRAO_COLUNAS = [
    13, 8, 9, 10, 4, 5, 6, 3, 12,
    16, 15, 14, 0, 1, 2, 7, 17, 11
]

VERSAO_CONFIG_TABELA = 2


class CampoAnimado(QLineEdit):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMouseTracking(True)

        self.setStyleSheet(
            """
            QLineEdit {
                background-color: white;
                color: black;
                border: 1px solid #cccccc;
                border-radius: 5px;
                padding: 5px;
            }

            QLineEdit:hover {
                background-color: #f4f9ff;
                border: 1px solid #5b9bd5;
            }

            QLineEdit:focus {
                background-color: #ffffff;
                border: 2px solid #4a90e2;
            }

            QLineEdit:read-only {
                background-color: #ffffff;
                color: black;
            }

            QLineEdit:read-only:hover {
                background-color: #f4f9ff;
                border: 1px solid #5b9bd5;
            }
            """
        )


# ============================================================
# CHECKBOX ANIMADO
# ============================================================

class CheckBoxAnimado(QCheckBox):

    def __init__(self, texto, parent=None):
        super().__init__(texto, parent)

        self.setMouseTracking(True)

        self.setStyleSheet(
            """
            QCheckBox {
                color: #111111;
                background-color: #ffffff;
                padding: 5px;
                border: 1px solid #d0d0d0;
                border-radius: 5px;
            }

            QCheckBox:hover {
                color: #0b3d91;
                background-color: #eaf3ff;
                border: 1px solid #5b9bd5;
            }

            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }

            QCheckBox::indicator:unchecked {
                border: 1px solid #999999;
                background-color: white;
                border-radius: 3px;
            }

            QCheckBox::indicator:unchecked:hover {
                border: 2px solid #5b9bd5;
                background-color: #f0f7ff;
            }

            QCheckBox::indicator:checked {
                border: 1px solid #357abd;
                background-color: #5b9bd5;
                border-radius: 3px;
            }
            """
        )


# ============================================================
# BOTÃO ANIMADO
# ============================================================

class BotaoAnimado(QPushButton):

    def __init__(self, texto, parent=None):
        super().__init__(texto, parent)

        self._animacao = QPropertyAnimation(
            self,
            b"geometry"
        )

        self._animacao.setDuration(120)

        self._animacao.setEasingCurve(
            QEasingCurve.OutCubic
        )

        self._geometria_original = None

        self.setCursor(
            Qt.PointingHandCursor
        )

        self.setMouseTracking(True)

        self.setStyleSheet(
            """
            QPushButton {
                background-color: #f0f0f0;
                color: #111111;
                border: 1px solid #bdbdbd;
                border-radius: 6px;
                padding: 8px 14px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #dcecff;
                color: #0b3d91;
                border: 1px solid #5b9bd5;
            }

            QPushButton:pressed {
                background-color: #b9d7f5;
                color: #082b66;
            }

            QPushButton:disabled {
                background-color: #dddddd;
                color: #888888;
            }
            """
        )

    def enterEvent(self, event):

        if self._geometria_original is None:
            self._geometria_original = self.geometry()

        geometria = self._geometria_original

        nova_geometria = geometria.adjusted(
            -2,
            -2,
            2,
            2
        )

        self._animacao.stop()

        self._animacao.setStartValue(
            self.geometry()
        )

        self._animacao.setEndValue(
            nova_geometria
        )

        self._animacao.start()

        super().enterEvent(event)

    def leaveEvent(self, event):

        if self._geometria_original is not None:

            self._animacao.stop()

            self._animacao.setStartValue(
                self.geometry()
            )

            self._animacao.setEndValue(
                self._geometria_original
            )

            self._animacao.start()

        super().leaveEvent(event)


# ============================================================
# TELA DE SENHA
# ============================================================

class TelaSenha(QWidget):

    def __init__(self):
        super().__init__()

        self.tela_banco = None

        self.setWindowTitle(
            "Acesso ao sistema"
        )

        self.setFixedSize(
            420,
            230
        )

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            30,
            25,
            30,
            25
        )

        titulo = QLabel(
            "Acesso ao sistema"
        )

        titulo.setAlignment(
            Qt.AlignCenter
        )

        titulo.setStyleSheet(
            """
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #0b3d91;
                padding: 8px;
            }
            """
        )

        layout.addWidget(
            titulo
        )

        descricao = QLabel(
            "Digite a senha para configurar "
            "a conexão com o banco de dados."
        )

        descricao.setAlignment(
            Qt.AlignCenter
        )

        descricao.setWordWrap(
            True
        )

        layout.addWidget(
            descricao
        )

        self.txtSenha = CampoAnimado()

        self.txtSenha.setPlaceholderText(
            "Senha de acesso"
        )

        self.txtSenha.setEchoMode(
            QLineEdit.Password
        )

        self.txtSenha.returnPressed.connect(
            self.verificar_senha
        )

        layout.addWidget(
            self.txtSenha
        )

        self.lblErro = QLabel()

        self.lblErro.setAlignment(
            Qt.AlignCenter
        )

        self.lblErro.setStyleSheet(
            """
            QLabel {
                color: #c00000;
                font-weight: bold;
            }
            """
        )

        layout.addWidget(
            self.lblErro
        )

        self.btEntrar = BotaoAnimado(
            "Continuar"
        )

        self.btEntrar.clicked.connect(
            self.verificar_senha
        )

        layout.addWidget(
            self.btEntrar
        )

        self.txtSenha.setFocus()

    def verificar_senha(self):

        senha = self.txtSenha.text()

        if senha == SENHA_ACESSO:

            self.lblErro.clear()

            self.btEntrar.setEnabled(
                False
            )

            self.tela_banco = TelaBancoDados()

            self.tela_banco.show()

            self.close()

        else:

            self.lblErro.setText(
                "Senha incorreta."
            )

            self.txtSenha.clear()

            self.txtSenha.setFocus()


# ============================================================
# TELA DE CONFIGURAÇÃO DO POSTGRESQL
# ============================================================

class TelaBancoDados(QWidget):

    def __init__(self):
        super().__init__()

        self.janela_principal = None
        self.conexao = None

        self.setWindowTitle(
            "Conexão com PostgreSQL"
        )

        self.setFixedSize(
            520,
            480
        )

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            30,
            25,
            30,
            25
        )

        # ====================================================
        # TÍTULO
        # ====================================================

        titulo = QLabel(
            "Conexão com banco de dados"
        )

        titulo.setAlignment(
            Qt.AlignCenter
        )

        titulo.setStyleSheet(
            """
            QLabel {
                font-size: 21px;
                font-weight: bold;
                color: #0b3d91;
                padding: 8px;
            }
            """
        )

        layout.addWidget(
            titulo
        )

        subtitulo = QLabel(
            "Banco de dados: PostgreSQL"
        )

        subtitulo.setAlignment(
            Qt.AlignCenter
        )

        subtitulo.setStyleSheet(
            """
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #444444;
                padding-bottom: 10px;
            }
            """
        )

        layout.addWidget(
            subtitulo
        )

        # ====================================================
        # GRUPO
        # ====================================================

        grupo = QGroupBox(
            "Dados da conexão"
        )

        formulario = QFormLayout(
            grupo
        )

        formulario.setContentsMargins(
            20,
            20,
            20,
            20
        )

        # ----------------------------------------------------
        # HOST
        # ----------------------------------------------------

        self.txtHost = CampoAnimado()

        self.txtHost.setPlaceholderText(
            "Ex.: 192.168.0.10"
        )

        formulario.addRow(
            "IP / Host:",
            self.txtHost
        )

        # ----------------------------------------------------
        # PORTA
        # ----------------------------------------------------

        self.txtPorta = CampoAnimado()

        self.txtPorta.setText(
            "5432"
        )

        self.txtPorta.setPlaceholderText(
            "5432"
        )

        formulario.addRow(
            "Porta:",
            self.txtPorta
        )

        # ----------------------------------------------------
        # BANCO
        # ----------------------------------------------------

        self.txtBanco = CampoAnimado()

        self.txtBanco.setPlaceholderText(
            "Nome do banco"
        )

        formulario.addRow(
            "Banco:",
            self.txtBanco
        )

        # ----------------------------------------------------
        # USUÁRIO
        # ----------------------------------------------------

        self.txtUsuario = CampoAnimado()

        self.txtUsuario.setPlaceholderText(
            "Usuário PostgreSQL"
        )

        formulario.addRow(
            "Usuário:",
            self.txtUsuario
        )

        # ----------------------------------------------------
        # SENHA DO BANCO
        # ----------------------------------------------------

        self.txtSenhaBanco = CampoAnimado()

        self.txtSenhaBanco.setPlaceholderText(
            "Senha PostgreSQL"
        )

        self.txtSenhaBanco.setEchoMode(
            QLineEdit.Password
        )

        formulario.addRow(
            "Senha:",
            self.txtSenhaBanco
        )

        layout.addWidget(
            grupo
        )

        # ====================================================
        # STATUS
        # ====================================================

        self.lblStatus = QLabel(
            "Informe os dados do PostgreSQL."
        )

        self.lblStatus.setWordWrap(
            True
        )

        self.lblStatus.setAlignment(
            Qt.AlignCenter
        )

        self.lblStatus.setStyleSheet(
            """
            QLabel {
                color: #444444;
                padding: 8px;
            }
            """
        )

        layout.addWidget(
            self.lblStatus
        )

        # ====================================================
        # BOTÃO TESTAR
        # ====================================================

        self.btConectar = BotaoAnimado(
            "Testar conexão e entrar"
        )

        self.btConectar.clicked.connect(
            self.testar_conexao
        )

        layout.addWidget(
            self.btConectar
        )

        # ====================================================
        # ENTER
        # ====================================================

        self.txtSenhaBanco.returnPressed.connect(
            self.testar_conexao
        )

        self.carregar_configuracao_banco()

    # ========================================================
    # ARQUIVO CONFIG BANCO
    # ========================================================

    def caminho_config_banco(self):

        return os.path.join(
            os.path.dirname(
                os.path.abspath(__file__)
            ),
            "config_banco.json"
        )

    # ========================================================
    # CARREGAR CONFIGURAÇÃO
    # ========================================================

    def carregar_configuracao_banco(self):

        caminho = self.caminho_config_banco()

        if not os.path.exists(
            caminho
        ):
            return

        try:

            with open(
                caminho,
                "r",
                encoding="utf-8"
            ) as arquivo:

                dados = json.load(
                    arquivo
                )

            self.txtHost.setText(
                str(
                    dados.get(
                        "host",
                        ""
                    )
                )
            )

            self.txtPorta.setText(
                str(
                    dados.get(
                        "porta",
                        "5432"
                    )
                )
            )

            self.txtBanco.setText(
                str(
                    dados.get(
                        "banco",
                        ""
                    )
                )
            )

            self.txtUsuario.setText(
                str(
                    dados.get(
                        "usuario",
                        ""
                    )
                )
            )

            # ------------------------------------------------
            # NÃO CARREGA A SENHA DO BANCO.
            # ------------------------------------------------
            #
            # Por segurança, ela deve ser digitada.
            #
            self.txtSenhaBanco.clear()

        except Exception:
            pass

    # ========================================================
    # SALVAR CONFIGURAÇÃO
    # ========================================================

    def salvar_configuracao_banco(self):

        dados = {
            "host": self.txtHost.text().strip(),
            "porta": self.txtPorta.text().strip(),
            "banco": self.txtBanco.text().strip(),
            "usuario": self.txtUsuario.text().strip(),
        }

        try:

            with open(
                self.caminho_config_banco(),
                "w",
                encoding="utf-8"
            ) as arquivo:

                json.dump(
                    dados,
                    arquivo,
                    ensure_ascii=False,
                    indent=4
                )

        except Exception:
            pass

    # ========================================================
    # TESTAR POSTGRESQL
    # ========================================================

    def testar_conexao(self):

        if psycopg2 is None:

            QMessageBox.critical(
                self,
                "PostgreSQL",
                (
                    "O módulo psycopg2 não está instalado.\n\n"
                    "Instale com:\n\n"
                    "pip install psycopg2-binary"
                )
            )

            return

        host = self.txtHost.text().strip()

        porta = self.txtPorta.text().strip()

        banco = self.txtBanco.text().strip()

        usuario = self.txtUsuario.text().strip()

        senha = self.txtSenhaBanco.text()

        # ====================================================
        # VALIDAÇÃO
        # ====================================================

        if not host:

            self.mostrar_erro(
                "Informe o IP / Host do PostgreSQL."
            )

            self.txtHost.setFocus()

            return

        if not porta:

            self.mostrar_erro(
                "Informe a porta do PostgreSQL."
            )

            self.txtPorta.setFocus()

            return

        try:

            porta_numero = int(
                porta
            )

        except ValueError:

            self.mostrar_erro(
                "A porta precisa ser um número."
            )

            self.txtPorta.setFocus()

            return

        if porta_numero < 1 or porta_numero > 65535:

            self.mostrar_erro(
                "A porta precisa estar entre 1 e 65535."
            )

            self.txtPorta.setFocus()

            return

        if not banco:

            self.mostrar_erro(
                "Informe o nome do banco."
            )

            self.txtBanco.setFocus()

            return

        if not usuario:

            self.mostrar_erro(
                "Informe o usuário do PostgreSQL."
            )

            self.txtUsuario.setFocus()

            return

        if not senha:

            self.mostrar_erro(
                "Informe a senha do PostgreSQL."
            )

            self.txtSenhaBanco.setFocus()

            return

        # ====================================================
        # BLOQUEIA BOTÃO
        # ====================================================

        self.btConectar.setEnabled(
            False
        )

        self.btConectar.setText(
            "Testando conexão..."
        )

        self.lblStatus.setText(
            "Conectando ao PostgreSQL..."
        )

        self.lblStatus.setStyleSheet(
            """
            QLabel {
                color: #0b3d91;
                font-weight: bold;
                padding: 8px;
            }
            """
        )

        QApplication.processEvents()

        conexao = None

        try:

            # =================================================
            # CONEXÃO REAL COM POSTGRESQL
            # =================================================

            conexao = psycopg2.connect(
                host=host,
                port=porta_numero,
                dbname=banco,
                user=usuario,
                password=senha,
                connect_timeout=5
            )

            # =================================================
            # TESTA A CONEXÃO
            # =================================================

            cursor = conexao.cursor()

            cursor.execute(
                "SELECT 1"
            )

            resultado = cursor.fetchone()

            cursor.close()

            if resultado != (1,):

                raise Exception(
                    "O PostgreSQL não retornou uma resposta válida."
                )

            # =================================================
            # CONEXÃO OK
            # =================================================

            self.conexao = conexao

            self.salvar_configuracao_banco()

            self.lblStatus.setText(
                "Conexão realizada com sucesso."
            )

            self.lblStatus.setStyleSheet(
                """
                QLabel {
                    color: #008000;
                    font-weight: bold;
                    padding: 8px;
                }
                """
            )

            QApplication.processEvents()

            # =================================================
            # ABRE A JANELA PRINCIPAL
            # =================================================

            self.janela_principal = Janela(
                conexao=self.conexao
            )

            self.janela_principal.show()

            # -------------------------------------------------
            # IMPORTANTE:
            # Não fecha a conexão aqui.
            # A janela principal passa a ser responsável por ela.
            # -------------------------------------------------

            self.close()

        except Exception as erro:

            # =================================================
            # SE DER ERRO, NÃO AVANÇA
            # =================================================

            if conexao is not None:

                try:
                    conexao.close()
                except Exception:
                    pass

            self.conexao = None

            self.btConectar.setEnabled(
                True
            )

            self.btConectar.setText(
                "Testar conexão e entrar"
            )

            self.mostrar_erro(
                self.traduzir_erro_postgres(
                    erro
                )
            )

            self.txtSenhaBanco.setFocus()

    # ========================================================
    # ERRO
    # ========================================================

    def mostrar_erro(self, mensagem):

        self.lblStatus.setText(
            mensagem
        )

        self.lblStatus.setStyleSheet(
            """
            QLabel {
                color: #c00000;
                font-weight: bold;
                padding: 8px;
            }
            """
        )

    # ========================================================
    # TRADUZIR ERROS COMUNS
    # ========================================================

    def traduzir_erro_postgres(
        self,
        erro
    ):

        texto = str(
            erro
        ).strip()

        texto_lower = texto.lower()

        if (
            "password authentication failed"
            in texto_lower
        ):

            return (
                "Senha do PostgreSQL incorreta.\n\n"
                "Confira o usuário e a senha."
            )

        if (
            "could not connect to server"
            in texto_lower
        ):

            return (
                "Não foi possível conectar ao PostgreSQL.\n\n"
                "Confira o IP/Host e a porta.\n\n"
                f"Detalhes: {texto}"
            )

        if (
            "connection refused"
            in texto_lower
        ):

            return (
                "A conexão foi recusada pelo PostgreSQL.\n\n"
                "Confira se o servidor PostgreSQL está "
                "ligado e se a porta está correta.\n\n"
                f"Detalhes: {texto}"
            )

        if (
            "timeout"
            in texto_lower
        ):

            return (
                "Tempo limite da conexão excedido.\n\n"
                "Confira o IP, porta e se o servidor está acessível.\n\n"
                f"Detalhes: {texto}"
            )

        if (
            "does not exist"
            in texto_lower
            and "database" in texto_lower
        ):

            return (
                "O banco de dados informado não existe.\n\n"
                f"Detalhes: {texto}"
            )

        if (
            "role"
            in texto_lower
            and "does not exist"
            in texto_lower
        ):

            return (
                "O usuário informado não existe no PostgreSQL.\n\n"
                f"Detalhes: {texto}"
            )

        return (
            "Não foi possível conectar ao PostgreSQL.\n\n"
            f"Detalhes:\n{texto}"
        )

# ============================================================
# TELA DE SENHA
# ============================================================

class TelaSenha(QWidget):

    def __init__(self):
        super().__init__()

        self.tela_banco = None

        self.setWindowTitle("Acesso ao Sistema")
        self.setFixedSize(420, 220)

        layout = QVBoxLayout(self)

        titulo = QLabel("Digite a senha para continuar")
        titulo.setAlignment(Qt.AlignCenter)

        titulo.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #222222;
                padding: 10px;
            }
        """)

        layout.addWidget(titulo)

        self.txtSenha = CampoAnimado()

        self.txtSenha.setPlaceholderText("Senha")
        self.txtSenha.setEchoMode(QLineEdit.Password)

        layout.addWidget(self.txtSenha)

        self.lblErro = QLabel("")
        self.lblErro.setAlignment(Qt.AlignCenter)

        self.lblErro.setStyleSheet("""
            QLabel {
                color: #c00000;
                font-weight: bold;
            }
        """)

        layout.addWidget(self.lblErro)

        self.btEntrar = BotaoAnimado("Continuar")

        self.btEntrar.clicked.connect(
            self.validar_senha
        )

        layout.addWidget(self.btEntrar)

        self.txtSenha.returnPressed.connect(
            self.validar_senha
        )

    def validar_senha(self):

        senha = self.txtSenha.text()

        # ====================================================
        # ALTERE AQUI PARA A SENHA DO SEU PROGRAMA
        # ====================================================

        SENHA_PROGRAMA = "1234"

        if senha != SENHA_PROGRAMA:

            self.lblErro.setText(
                "Senha incorreta."
            )

            self.txtSenha.clear()
            self.txtSenha.setFocus()

            return

        # ====================================================
        # SENHA CORRETA
        # ====================================================
        # NÃO ABRE A JANELA PRINCIPAL.
        #
        # Primeiro abre a tela do PostgreSQL.
        # ====================================================

        self.lblErro.setText("")

        self.btEntrar.setEnabled(False)

        self.tela_banco = TelaBancoDados()

        self.tela_banco.show()

        self.close()


# ============================================================
# TELA DE CONFIGURAÇÃO / CONEXÃO POSTGRESQL
# ============================================================

class TelaBancoDados(QWidget):

    def __init__(self):
        super().__init__()

        self.janela_principal = None
        self.conexao = None

        self.setWindowTitle(
            "Conexão com Banco de Dados PostgreSQL"
        )

        self.setFixedSize(
            520,
            430
        )

        layout = QVBoxLayout(self)

        # ====================================================
        # TITULO
        # ====================================================

        titulo = QLabel(
            "Configuração do Banco de Dados"
        )

        titulo.setAlignment(
            Qt.AlignCenter
        )

        titulo.setStyleSheet("""
            QLabel {
                font-size: 19px;
                font-weight: bold;
                color: #222222;
                padding: 10px;
            }
        """)

        layout.addWidget(titulo)

        # ====================================================
        # BANCO
        # ====================================================

        lblBanco = QLabel(
            "Banco de dados:"
        )

        layout.addWidget(
            lblBanco
        )

        self.txtBanco = CampoAnimado()

        self.txtBanco.setText(
            "postgres"
        )

        self.txtBanco.setReadOnly(
            True
        )

        layout.addWidget(
            self.txtBanco
        )

        # ====================================================
        # IP / HOST
        # ====================================================

        lblHost = QLabel(
            "IP / Host:"
        )

        layout.addWidget(
            lblHost
        )

        self.txtHost = CampoAnimado()

        self.txtHost.setPlaceholderText(
            "Ex.: 192.168.0.100"
        )

        layout.addWidget(
            self.txtHost
        )

        # ====================================================
        # PORTA
        # ====================================================

        lblPorta = QLabel(
            "Porta:"
        )

        layout.addWidget(
            lblPorta
        )

        self.txtPorta = CampoAnimado()

        self.txtPorta.setText(
            "5432"
        )

        layout.addWidget(
            self.txtPorta
        )

        # ====================================================
        # USUARIO
        # ====================================================

        lblUsuario = QLabel(
            "Usuário:"
        )

        layout.addWidget(
            lblUsuario
        )

        self.txtUsuario = CampoAnimado()

        self.txtUsuario.setPlaceholderText(
            "Usuário do PostgreSQL"
        )

        layout.addWidget(
            self.txtUsuario
        )

        # ====================================================
        # SENHA DO POSTGRES
        # ====================================================

        lblSenha = QLabel(
            "Senha do PostgreSQL:"
        )

        layout.addWidget(
            lblSenha
        )

        self.txtSenhaBanco = CampoAnimado()

        self.txtSenhaBanco.setEchoMode(
            QLineEdit.Password
        )

        layout.addWidget(
            self.txtSenhaBanco
        )

        # ====================================================
        # STATUS
        # ====================================================

        self.lblStatus = QLabel(
            ""
        )

        self.lblStatus.setWordWrap(
            True
        )

        self.lblStatus.setAlignment(
            Qt.AlignCenter
        )

        layout.addWidget(
            self.lblStatus
        )

        # ====================================================
        # BOTÃO TESTAR
        # ====================================================

        self.btTestar = BotaoAnimado(
            "Testar Conexão"
        )

        self.btTestar.clicked.connect(
            self.testar_conexao
        )

        layout.addWidget(
            self.btTestar
        )

        # ====================================================
        # BOTÃO ENTRAR
        # ====================================================

        self.btEntrar = BotaoAnimado(
            "Conectar e Abrir Sistema"
        )

        self.btEntrar.setEnabled(
            False
        )

        self.btEntrar.clicked.connect(
            self.conectar_e_abrir
        )

        layout.addWidget(
            self.btEntrar
        )

    # ========================================================
    # PEGAR DADOS
    # ========================================================

    def obter_dados(self):

        host = self.txtHost.text().strip()

        porta = self.txtPorta.text().strip()

        usuario = self.txtUsuario.text().strip()

        senha = self.txtSenhaBanco.text()

        banco = "postgres"

        return {
            "host": host,
            "port": porta,
            "user": usuario,
            "password": senha,
            "dbname": banco,
        }

    # ========================================================
    # TESTAR CONEXÃO
    # ========================================================

    def testar_conexao(self):

        if psycopg2 is None:

            self.lblStatus.setStyleSheet("""
                QLabel {
                    color: #c00000;
                    font-weight: bold;
                }
            """)

            self.lblStatus.setText(
                "O módulo psycopg2 não está instalado.\n"
                "Instale com:\n"
                "pip install psycopg2-binary"
            )

            return

        dados = self.obter_dados()

        if not dados["host"]:

            self.lblStatus.setStyleSheet("""
                QLabel {
                    color: #c00000;
                    font-weight: bold;
                }
            """)

            self.lblStatus.setText(
                "Informe o IP / Host do PostgreSQL."
            )

            self.txtHost.setFocus()

            return

        if not dados["porta"]:

            self.lblStatus.setStyleSheet("""
                QLabel {
                    color: #c00000;
                    font-weight: bold;
                }
            """)

            self.lblStatus.setText(
                "Informe a porta do PostgreSQL."
            )

            self.txtPorta.setFocus()

            return

        if not dados["user"]:

            self.lblStatus.setStyleSheet("""
                QLabel {
                    color: #c00000;
                    font-weight: bold;
                }
            """)

            self.lblStatus.setText(
                "Informe o usuário do PostgreSQL."
            )

            self.txtUsuario.setFocus()

            return

        if not dados["password"]:

            self.lblStatus.setStyleSheet("""
                QLabel {
                    color: #c00000;
                    font-weight: bold;
                }
            """)

            self.lblStatus.setText(
                "Informe a senha do PostgreSQL."
            )

            self.txtSenhaBanco.setFocus()

            return

        try:

            porta = int(
                dados["port"]
            )

        except ValueError:

            self.lblStatus.setStyleSheet("""
                QLabel {
                    color: #c00000;
                    font-weight: bold;
                }
            """)

            self.lblStatus.setText(
                "A porta precisa ser numérica."
            )

            self.txtPorta.setFocus()

            return

        self.btTestar.setEnabled(
            False
        )

        self.btEntrar.setEnabled(
            False
        )

        self.lblStatus.setStyleSheet("""
            QLabel {
                color: #174ea6;
                font-weight: bold;
            }
        """)

        self.lblStatus.setText(
            "Testando conexão com PostgreSQL..."
        )

        QApplication.processEvents()

        conexao_teste = None

        try:

            conexao_teste = psycopg2.connect(
                host=dados["host"],
                port=porta,
                user=dados["user"],
                password=dados["password"],
                dbname=dados["dbname"],
                connect_timeout=5
            )

            cursor = conexao_teste.cursor()

            cursor.execute(
                "SELECT version();"
            )

            resultado = cursor.fetchone()

            cursor.close()

            conexao_teste.close()

            conexao_teste = None

            self.lblStatus.setStyleSheet("""
                QLabel {
                    color: #008000;
                    font-weight: bold;
                }
            """)

            self.lblStatus.setText(
                "CONEXÃO OK!\n"
                "PostgreSQL respondeu corretamente."
            )

            self.btEntrar.setEnabled(
                True
            )

        except Exception as erro:

            if conexao_teste is not None:

                try:
                    conexao_teste.close()
                except Exception:
                    pass

            self.lblStatus.setStyleSheet("""
                QLabel {
                    color: #c00000;
                    font-weight: bold;
                }
            """)

            self.lblStatus.setText(
                "FALHA NA CONEXÃO.\n\n"
                + str(erro)
            )

            self.btEntrar.setEnabled(
                False
            )

        finally:

            self.btTestar.setEnabled(
                True
            )

    # ========================================================
    # CONECTAR E ABRIR SISTEMA
    # ========================================================

    def conectar_e_abrir(self):

        if psycopg2 is None:

            QMessageBox.critical(
                self,
                "Erro",
                "O módulo psycopg2 não está instalado.\n\n"
                "Execute:\n"
                "pip install psycopg2-binary"
            )

            return

        dados = self.obter_dados()

        try:

            porta = int(
                dados["port"]
            )

        except ValueError:

            QMessageBox.critical(
                self,
                "Erro",
                "A porta do PostgreSQL é inválida."
            )

            return

        self.btEntrar.setEnabled(
            False
        )

        self.btTestar.setEnabled(
            False
        )

        self.lblStatus.setStyleSheet("""
            QLabel {
                color: #174ea6;
                font-weight: bold;
            }
        """)

        self.lblStatus.setText(
            "Estabelecendo conexão..."
        )

        QApplication.processEvents()

        try:

            self.conexao = psycopg2.connect(
                host=dados["host"],
                port=porta,
                user=dados["user"],
                password=dados["password"],
                dbname="postgres",
                connect_timeout=5
            )

            # =================================================
            # TESTE REAL
            # =================================================

            cursor = self.conexao.cursor()

            cursor.execute(
                "SELECT 1;"
            )

            resultado = cursor.fetchone()

            cursor.close()

            if resultado is None:

                raise Exception(
                    "O PostgreSQL não retornou uma resposta válida."
                )

            # =================================================
            # SOMENTE AQUI A TELA PRINCIPAL É CRIADA
            # =================================================

            self.janela_principal = Janela()

            # Guarda a conexão na janela principal
            self.janela_principal.conexao_banco = (
                self.conexao
            )

            self.janela_principal.config_banco = {
                "host": dados["host"],
                "port": porta,
                "user": dados["user"],
                "dbname": "postgres",
            }

            self.janela_principal.show()

            self.close()

        except Exception as erro:

            if self.conexao is not None:

                try:
                    self.conexao.close()
                except Exception:
                    pass

                self.conexao = None

            self.btEntrar.setEnabled(
                False
            )

            self.btTestar.setEnabled(
                True
            )

            self.lblStatus.setStyleSheet("""
                QLabel {
                    color: #c00000;
                    font-weight: bold;
                }
            """)

            self.lblStatus.setText(
                "NÃO FOI POSSÍVEL CONECTAR.\n\n"
                + str(erro)
            )

            QMessageBox.critical(
                self,
                "Falha na conexão",
                "A conexão com o PostgreSQL falhou.\n\n"
                "Verifique:\n"
                "• IP / Host\n"
                "• Porta\n"
                "• Usuário\n"
                "• Senha\n"
                "• Servidor PostgreSQL\n"
                "• Rede\n\n"
                f"Erro:\n{erro}"
            )

# ============================================================
# BASE LOCAL DE QUANTIDADE POR EMBALAGEM
# ============================================================

BASE_EMBALAGENS_PADRAO = {
    # EAN da unidade -> quantidade por caixa/master.
    # O primeiro registro foi confirmado no catálogo Ypê e em distribuidores.
    "7896098902400": {
        "quantidade": 6,
        "fonte": "Catálogo Ypê / Multicanal Atacado",
        "ean_master": "27896098902404"
    },
    # Outros registros do mesmo catálogo/listagem, para a base já começar útil.
    "7896098900406": {"quantidade": 24, "fonte": "Multicanal Atacado", "ean_master": ""},
    "7896098902394": {"quantidade": 6, "fonte": "Multicanal Atacado", "ean_master": ""},
    "7896098902424": {"quantidade": 6, "fonte": "Multicanal Atacado", "ean_master": ""},
    "7896098903032": {"quantidade": 6, "fonte": "Multicanal Atacado", "ean_master": ""},
    "7896098902417": {"quantidade": 6, "fonte": "Multicanal Atacado", "ean_master": ""},
    "7896098903674": {"quantidade": 6, "fonte": "Multicanal Atacado", "ean_master": ""},
    "7896098903605": {"quantidade": 12, "fonte": "Multicanal Atacado", "ean_master": ""},
    "7896098903506": {"quantidade": 4, "fonte": "Multicanal Atacado", "ean_master": ""},
}


def _normalizar_ean(ean):
    return re.sub(r"\D", "", str(ean or ""))


def _caminho_base_embalagens():
    pasta = os.path.join(
        os.environ.get("APPDATA", os.path.expanduser("~")),
        "XML"
    )
    os.makedirs(pasta, exist_ok=True)
    return os.path.join(pasta, "embalagens.json")


def carregar_base_embalagens():
    caminho = _caminho_base_embalagens()
    base = {}

    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as arquivo:
                dados = json.load(arquivo)
            if isinstance(dados, dict):
                base.update(dados)
        except Exception:
            pass

    # Garante que o exemplo já confirmado esteja disponível.
    alterou = False
    for ean, dados in BASE_EMBALAGENS_PADRAO.items():
        if ean not in base:
            base[ean] = dados
            alterou = True

    if alterou or not os.path.exists(caminho):
        salvar_base_embalagens(base)

    return base


def salvar_base_embalagens(base):
    caminho = _caminho_base_embalagens()
    tmp = caminho + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as arquivo:
            json.dump(base, arquivo, ensure_ascii=False, indent=4)
        os.replace(tmp, caminho)
        return True
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        return False


def obter_embalagem_local(base, ean):
    ean = _normalizar_ean(ean)
    if not ean:
        return None

    dados = base.get(ean)
    if not isinstance(dados, dict):
        return None

    try:
        quantidade = int(dados.get("quantidade", 0))
    except Exception:
        quantidade = 0

    if quantidade <= 0:
        return None

    return {
        "quantidade": quantidade,
        "fonte": str(dados.get("fonte", "Base local") or "Base local"),
        "ean_master": str(dados.get("ean_master", "") or "")
    }


# ============================================================
# PESQUISA MANUAL NA INTERNET
# ============================================================

class _ResultadoBuscaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.textos = []
        self.urls = []
        self._buffer = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        href = attrs.get("href", "")
        if href.startswith("http"):
            self.urls.append(href)

    def handle_data(self, data):
        texto = " ".join(str(data).split())
        if texto:
            self._buffer.append(texto)

    def handle_endtag(self, tag):
        if self._buffer:
            texto = " ".join(self._buffer)
            if texto:
                self.textos.append(texto)
            self._buffer = []


def _calcular_dun14(ean, indicador=2):
    ean = _normalizar_ean(ean)
    if len(ean) != 13:
        return None

    corpo = str(indicador) + ean[:-1]
    total = 0
    for pos, digito in enumerate(reversed(corpo)):
        total += int(digito) * (3 if pos % 2 == 0 else 1)
    check = (10 - (total % 10)) % 10
    return corpo + str(check)


def _candidatos_ean(ean):
    ean = _normalizar_ean(ean)
    candidatos = []
    if ean:
        candidatos.append(ean)
    if len(ean) == 13:
        for indicador in range(1, 9):
            dun = _calcular_dun14(ean, indicador)
            if dun and dun not in candidatos:
                candidatos.append(dun)
    return candidatos


def _limpar_texto_web(texto):
    texto = _html.unescape(str(texto or ""))
    texto = re.sub(r"<script.*?</script>", " ", texto, flags=re.I | re.S)
    texto = re.sub(r"<style.*?</style>", " ", texto, flags=re.I | re.S)
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = texto.replace("×", "x")
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def _extrair_fator_embalagem(texto):
    texto = _limpar_texto_web(texto)
    if not texto:
        return None

    padroes = [
        # Formatos de distribuidores: CX/0006/UN, CX/6/UN, CX-0006, etc.
        r"\b(?:cx|caixa|fardo|fd)\s*[/\\-]\s*0*(\d{1,3})(?:\s*[/\\-]\s*(?:un|und|unid|unidades?))?\b",
        # Texto explícito: caixa com 6 unidades.
        r"\b(?:caixa|cx|fardo|fd|pack|pacote|embalagem)\s*(?:master)?\s*(?:com|de)\s*(\d{1,3})\s*(?:un|und|unid(?:ades)?|unidades)\b",
        # Multiplicação: 6 x 2L, 12 x 500ml, etc.
        r"\b(\d{1,3})\s*x\s*\d+(?:[.,]\d+)?\s*(?:ml|l|g|kg|mg|litros?|gramas?)\b",
        # Quantidade por caixa/embalagem.
        r"\b(\d{1,3})\s*(?:un|und|unid(?:ades)?|unidades)\s*(?:por|/|em)\s*(?:caixa|cx|fardo|fd|embalagem)\b",
        # Campo de cadastro: Quantidade: 6 unidades.
        r"\b(?:quantidade|qtd)\s*[:=-]?\s*(\d{1,3})\s*(?:un|und|unid(?:ades)?|unidades)\b",
        # Campo comum em catálogos: Embalagem: CX/0006/UN.
        r"\bembalagem\s*[:=-]?\s*(?:cx|caixa|fardo|fd)\s*[/\\-]\s*0*(\d{1,3})\s*(?:[/\\-]\s*(?:un|und|unid|unidades?))?\b",
    ]

    for padrao in padroes:
        m = re.search(padrao, texto, re.IGNORECASE)
        if m:
            try:
                valor = int(m.group(1))
                if 1 <= valor <= 999:
                    return valor
            except Exception:
                pass
    return None


def _buscar_duckduckgo_rapido(ean):
    candidatos = _candidatos_ean(ean)
    consultas = []
    # Poucas consultas, mas mais úteis. A pesquisa em lote já roda em paralelo.
    for codigo in candidatos[:3]:
        consultas.extend([
            '"{}" "Embalagem" "EAN"'.format(codigo),
            '"{}" "CX/"'.format(codigo),
            '"{}" "caixa com"'.format(codigo),
        ])

    for consulta in consultas:
        try:
            url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(consulta)
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"
                }
            )
            with urllib.request.urlopen(req, timeout=2) as resposta:
                pagina = resposta.read().decode("utf-8", "ignore")

            parser = _ResultadoBuscaParser()
            parser.feed(pagina)
            texto = " ".join(parser.textos)
            fator = _extrair_fator_embalagem(texto)
            if fator:
                return fator, "Pesquisa web"
        except Exception:
            continue

    return None, "Não encontrado"


class _ResultadoPesquisaManual(QObject):
    resultado = Signal(str, object, str)


class _PesquisaEmbalagemWorker(QRunnable):
    def __init__(self, ean):
        super().__init__()
        self.setAutoDelete(False)
        self.ean = _normalizar_ean(ean)
        self.sinais = _ResultadoPesquisaManual()

    def run(self):
        # Caso conhecido: evita depender da internet.
        if self.ean == "7896098902400":
            self.sinais.resultado.emit(
                self.ean,
                6,
                "Catálogo/embalagem master Ypê"
            )
            return

        fator, fonte = _buscar_duckduckgo_rapido(self.ean)
        self.sinais.resultado.emit(self.ean, fator, fonte)


# ============================================================
# JANELA PRINCIPAL

# ============================================================

class Janela(QMainWindow):

    def __init__(self, conexao=None):
        super().__init__()

        # ====================================================
        # CONFIGURAÇÃO DA JANELA
        # ====================================================

        self.setWindowTitle("XML")
        self.resize(1300, 750)

        # ====================================================
        # CONEXÃO POSTGRESQL
        # ====================================================

        self.conexao = conexao

        # ====================================================
        # DADOS
        # ====================================================

        self.produtos = []

        # ====================================================
        # BASE LOCAL DE EMBALAGENS
        # ====================================================

        self._base_embalagens = carregar_base_embalagens()
        self._workers_qtd_embalagem = []
        self._pool_qtd_embalagem = QThreadPool.globalInstance()
        # Pesquisa em lote dos EANs ainda não cadastrados.
        self._pesquisa_lote_ativa = False
        self._pesquisa_lote_pendentes = set()
        self._pesquisa_lote_total = 0
        self._pesquisa_lote_concluidos = 0

        # ====================================================
        # DADOS DA NOTA ATUAL
        # ====================================================

        self.chave_nfe = ""

        self.formas_pagamento = []

        self.pagamento_texto = ""

        # ====================================================
        # CONTROLE DAS COLUNAS
        # ====================================================

        self.coluna_selecionada = -1

        # ====================================================
        # MODO SELECIONAR CÉLULAS
        # ====================================================

        self._celulas_selecionadas = set()

        self.alinhamento_colunas = {}

        self._ordem_colunas_original = list(
            range(16)
        )

        self._larguras_colunas_original = {}

        self.colunas_fixadas = set()

        # ====================================================
        # ARQUIVO DE CONFIGURAÇÃO
        # ====================================================

        pasta_configuracao = os.path.join(
            os.environ.get("APPDATA", os.path.expanduser("~")),
            "XML"
        )

        os.makedirs(
            pasta_configuracao,
            exist_ok=True
        )

        self.arquivo_configuracao = os.path.join(
            pasta_configuracao,
            "config_tabela.json"
        )

        # ====================================================
        # JANELA PRINCIPAL
        # ====================================================

        central = QWidget()

        self.setCentralWidget(
            central
        )

        layout = QVBoxLayout(
            central
        )

        # ====================================================
        # BOTÕES
        # ====================================================

        botoes = QHBoxLayout()

        self.btAbrir = BotaoAnimado(
            "Abrir PDF / Baixar XML"
        )

        self.btAbrir.clicked.connect(
            self.abrir_pdf
        )

        botoes.addWidget(
            self.btAbrir
        )

        self.btPasta = BotaoAnimado(
            "Abrir Pasta XML"
        )

        self.btPasta.clicked.connect(
            self.abrir_pasta
        )

        botoes.addWidget(
            self.btPasta
        )

        self.btSalvar = BotaoAnimado(
            "Salvar"
        )

        self.btSalvar.clicked.connect(
            self.salvar_configuracao
        )

        botoes.addWidget(
            self.btSalvar
        )

        self.btColuna = BotaoAnimado(
            "Coluna"
        )

        self.btColuna.clicked.connect(
            self.abrir_menu_coluna
        )

        botoes.addWidget(
            self.btColuna
        )

        self.btPesquisarEAN = BotaoAnimado(
            "Pesquisar EAN"
        )
        self.btPesquisarEAN.setToolTip(
            "Pesquisa o EAN selecionado na internet e salva o resultado na base local."
        )
        self.btPesquisarEAN.clicked.connect(
            self.pesquisar_ean_selecionado
        )
        botoes.addWidget(
            self.btPesquisarEAN
        )

        self.btPesquisarNaoCadastrados = BotaoAnimado(
            "Pesquisar não cadastrados"
        )
        self.btPesquisarNaoCadastrados.setToolTip(
            "Pesquisa somente os EANs que estão como Não cadastrado e salva os resultados na base local."
        )
        self.btPesquisarNaoCadastrados.clicked.connect(
            self.pesquisar_eans_nao_cadastrados
        )
        botoes.addWidget(
            self.btPesquisarNaoCadastrados
        )

        # ====================================================
        # CHECKBOX SELECIONAR CÉLULAS
        # ====================================================

        self.chkSelecionar = CheckBoxAnimado(
            "Selecionar"
        )

        self.chkSelecionar.setToolTip(
            "Ativa a seleção manual de células. As células selecionadas ficam laranja."
        )

        self.chkSelecionar.stateChanged.connect(
            self.alternar_modo_selecao
        )

        botoes.addWidget(
            self.chkSelecionar
        )

        botoes.addStretch()

        layout.addLayout(
            botoes
        )

        # ====================================================
        # PESQUISA
        # ====================================================

        pesquisa = QHBoxLayout()

        self.txtPesquisa = CampoAnimado()

        self.txtPesquisa.setPlaceholderText(
            "Pesquisar codigo, produto, NF ou chave..."
        )

        self.txtPesquisa.textChanged.connect(
            self.filtrar
        )

        pesquisa.addWidget(
            self.txtPesquisa
        )

        self.txtEmbalagem = CampoAnimado()

        self.txtEmbalagem.setPlaceholderText(
            "Filtrar Emb (UN, CX, KG...)"
        )

        self.txtEmbalagem.textChanged.connect(
            self.filtrar
        )

        pesquisa.addWidget(
            self.txtEmbalagem
        )

        self.chkEmbDiferenteUN = CheckBoxAnimado(
            "Emb diferente de UN"
        )

        self.chkEmbDiferenteUN.stateChanged.connect(
            self.filtrar
        )

        pesquisa.addWidget(
            self.chkEmbDiferenteUN
        )

        layout.addLayout(
            pesquisa
        )

        # ====================================================
        # RESUMO
        # ====================================================

        self.lblFornecedor = QLabel(
            "Fornecedor:"
        )

        # Nome do fornecedor conforme o nome do arquivo PDF selecionado.
        # Este campo e adicional e nao altera o fornecedor lido do XML.
        self.lblFornArquivo = QLabel(
            ""
        )

        self.lblFornArquivo.setStyleSheet(
            """
            QLabel {
                font-weight: bold;
                color: #d6b300;
            }
            """
        )

        self.lblNF = QLabel(
            "NF:"
        )

        # Os campos de fornecedor, FORN (nome do arquivo) e NF
        # podem ser clicados para copiar o texto para a area de transferencia.
        for _label in (
            self.lblFornecedor,
            self.lblFornArquivo,
            self.lblNF,
        ):
            _label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            _label.setCursor(
                Qt.CursorShape.IBeamCursor
            )

        self.lblFornecedor.mousePressEvent = (
            lambda event, label=self.lblFornecedor:
            self.copiar_texto_label(label, event)
        )
        self.lblFornArquivo.mousePressEvent = (
            lambda event, label=self.lblFornArquivo:
            self.copiar_texto_label(label, event)
        )
        self.lblNF.mousePressEvent = (
            lambda event, label=self.lblNF:
            self.copiar_texto_label(label, event)
        )

        self.lblChave = QLabel(
            "Chave NF-e:"
        )

        self.txtChave = CampoAnimado()

        self.txtChave.setReadOnly(
            True
        )

        self.txtChave.setPlaceholderText(
            "Chave NF-e"
        )

        self.lblPagamento = QLabel(
            "Forma de Pagamento:"
        )

        # Exibição da forma de pagamento com destaque individual
        # para o valor da parcela e para a data de vencimento.
        self.txtPagamento = QLabel(
            "Forma de Pagamento"
        )

        self.txtPagamento.setWordWrap(
            True
        )

        self.txtPagamento.setTextFormat(
            Qt.RichText
        )

        self.txtPagamento.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )

        self.txtPagamento.setStyleSheet(
            """
            QLabel {
                background-color: white;
                color: black;
                border: 1px solid #cccccc;
                border-radius: 5px;
                padding: 5px;
            }
            """
        )

        self.lblQtd = QLabel(
            "Produtos: 0"
        )

        # FORNECEDOR + NF NA MESMA LINHA
        linha_fornecedor_nf = QHBoxLayout()
        linha_fornecedor_nf.setContentsMargins(0, 0, 0, 0)
        linha_fornecedor_nf.setSpacing(18)

        linha_fornecedor_nf.addWidget(
            self.lblFornecedor
        )

        linha_fornecedor_nf.addWidget(
            self.lblFornArquivo
        )

        linha_fornecedor_nf.addWidget(
            self.lblNF
        )

        linha_fornecedor_nf.addStretch()

        layout.addLayout(
            linha_fornecedor_nf
        )

        layout.addWidget(
            self.lblChave
        )

        layout.addWidget(
            self.txtChave
        )

        layout.addWidget(
            self.lblPagamento
        )

        layout.addWidget(
            self.txtPagamento
        )

        layout.addWidget(
            self.lblQtd
        )

        # ====================================================
        # TABELA
        # ====================================================

        self.tabela = QTableWidget()

        self.tabela.setColumnCount(
            18
        )

        self.tabela.setHorizontalHeaderLabels([
            "Codigo ERP",
            "Descricao ERP",
            "Pr Cpra ERP",
            "Qtd Ult Ent",
            "Pr Ult Cpra Unit.",
            "Pr Ult Cpra Ant",
            "Dt Ult Compra",
            "Cod F",
            "Descricao XML",
            "Emb",
            "QUANT",
            "Qtd/Emb.",
            "Mult",
            "SEQ",
            "Valor XML",
            "Valor UN XML",
            "Qtd Total",
            "Cod Barras XML"
        ])

        self.tabela.setAlternatingRowColors(
            False
        )

        self.tabela.setMouseTracking(
            True
        )

        self.tabela.setEditTriggers(
            QTableWidget.NoEditTriggers
        )

        self.tabela.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )

        self.tabela.setVerticalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )

        self.tabela.cellClicked.connect(
            self.selecionar_coluna
        )

        self.tabela.cellClicked.connect(
            self.alternar_selecao_celula
        )

        self.tabela.horizontalHeader().sectionClicked.connect(
            self.selecionar_coluna_header
        )

        self.tabela.horizontalHeader().setSectionsMovable(
            True
        )

        self.tabela.horizontalHeader().setSectionsClickable(
            True
        )

        self.tabela.horizontalHeader().setContextMenuPolicy(
            Qt.CustomContextMenu
        )

        self.tabela.horizontalHeader().customContextMenuRequested.connect(
            self.abrir_menu_coluna_direito
        )

        self.tabela.setContextMenuPolicy(
            Qt.CustomContextMenu
        )

        self.tabela.customContextMenuRequested.connect(
            self.abrir_menu_coluna_celula
        )

        self.tabela.setSelectionBehavior(
            QTableWidget.SelectItems
        )

        self.tabela.setSelectionMode(
            QTableWidget.SingleSelection
        )

        self.tabela.setSortingEnabled(
            False
        )

        self.tabela.horizontalHeader().setStretchLastSection(
            False
        )

        # ====================================================
        # LARGURAS
        # ====================================================

        for indice in range(
            self.tabela.columnCount()
        ):

            self._larguras_colunas_original[indice] = (
                self.tabela.columnWidth(
                    indice
                )
            )

        # ====================================================
        # ESTILO
        # ====================================================

        self.tabela.setStyleSheet(
            """
            QTableWidget {
                background-color: white;
                color: black;
                gridline-color: #d0d0d0;
                selection-background-color: #dcecff;
                selection-color: black;
            }

            QTableWidget::item:hover {
                background-color: #eaf4ff;
                color: #0b3d91;
            }

            QTableWidget::item:selected {
                background-color: #dcecff;
                color: black;
            }

            QTableWidget::item:selected:active {
                background-color: #dcecff;
                color: black;
            }

            QScrollBar:horizontal {
                background: #d0d0d0;
                height: 14px;
                margin: 0px;
            }

            QScrollBar::handle:horizontal {
                background: #222222;
                min-width: 30px;
                border-radius: 2px;
            }

            QScrollBar::handle:horizontal:hover {
                background: #000000;
            }

            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                background: #bdbdbd;
                width: 14px;
            }

            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: #e5e5e5;
            }

            QScrollBar:vertical {
                background: #d0d0d0;
                width: 14px;
                margin: 0px;
            }

            QScrollBar::handle:vertical {
                background: #222222;
                min-height: 30px;
                border-radius: 2px;
            }

            QScrollBar::handle:vertical:hover {
                background: #000000;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                background: #bdbdbd;
                height: 14px;
            }

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: #e5e5e5;
            }

            QHeaderView::section {
                background-color: #eeeeee;
                color: #111111;
                padding: 5px;
                border: 1px solid #cccccc;
                font-weight: bold;
            }

            QHeaderView::section:hover {
                background-color: #dcecff;
                color: #0b3d91;
            }
            """
        )

        layout.addWidget(
            self.tabela
        )

        self.carregar_configuracao()

    # ========================================================
    # FECHAMENTO
    # ========================================================

    def closeEvent(self, event):

        if self.conexao is not None:

            try:

                if not self.conexao.closed:

                    self.conexao.close()

            except Exception:
                pass

        event.accept()

    # ========================================================
    # TESTE DA CONEXÃO
    # ========================================================

    def banco_conectado(self):

        if self.conexao is None:
            return False

        try:

            if self.conexao.closed:
                return False

            cursor = self.conexao.cursor()

            cursor.execute(
                "SELECT 1"
            )

            resultado = cursor.fetchone()

            cursor.close()

            return resultado == (1,)

        except Exception:

            return False

    # ========================================================
    # SALVAR CONFIGURAÇÃO DA TABELA
    # ========================================================

    def salvar_configuracao(self):

        try:

            header = self.tabela.horizontalHeader()

            ordem = []

            for visual in range(
                self.tabela.columnCount()
            ):

                ordem.append(
                    header.logicalIndex(visual)
                )

            larguras = {}

            ocultas = []

            for coluna in range(
                self.tabela.columnCount()
            ):

                larguras[str(coluna)] = (
                    self.tabela.columnWidth(coluna)
                )

                if self.tabela.isColumnHidden(coluna):
                    ocultas.append(coluna)

            fixadas = list(self.colunas_fixadas)

            alinhamentos = {}

            for coluna, alinhamento in (
                self.alinhamento_colunas.items()
            ):

                alinhamentos[str(coluna)] = int(alinhamento)

            configuracao = {
                "versao": VERSAO_CONFIG_TABELA,
                "ordem": ordem,
                "larguras": larguras,
                "ocultas": ocultas,
                "fixadas": fixadas,
                "alinhamentos": alinhamentos,
            }

            with open(
                self.arquivo_configuracao,
                "w",
                encoding="utf-8"
            ) as arquivo:

                json.dump(
                    configuracao,
                    arquivo,
                    ensure_ascii=False,
                    indent=4
                )

            QMessageBox.information(
                self,
                "Salvar",
                "Configuracao da tabela salva com sucesso."
            )

        except Exception as erro:

            QMessageBox.critical(
                self,
                "Erro ao salvar",
                str(erro)
            )

    # ========================================================
    # CARREGAR CONFIGURAÇÃO
    # ========================================================

    def aplicar_ordem_padrao(self):

        header = self.tabela.horizontalHeader()

        for visual_destino, coluna_logica in enumerate(
            ORDEM_PADRAO_COLUNAS
        ):

            visual_atual = header.visualIndex(
                coluna_logica
            )

            if visual_atual != visual_destino:

                header.moveSection(
                    visual_atual,
                    visual_destino
                )

    def carregar_configuracao(self):

        if not os.path.exists(
            self.arquivo_configuracao
        ):

            self.aplicar_ordem_padrao()

            return

        try:

            with open(
                self.arquivo_configuracao,
                "r",
                encoding="utf-8"
            ) as arquivo:

                configuracao = json.load(arquivo)

            versao = int(
                configuracao.get("versao", 0)
            )

            if versao != VERSAO_CONFIG_TABELA:

                self.aplicar_ordem_padrao()

                return

            header = self.tabela.horizontalHeader()

            ordem = [
                int(coluna)
                for coluna in configuracao.get("ordem", [])
            ]

            if (
                len(ordem) != self.tabela.columnCount()
                or sorted(ordem)
                != list(range(self.tabela.columnCount()))
            ):

                self.aplicar_ordem_padrao()

            else:

                for visual_destino, logico in enumerate(ordem):

                    visual_atual = header.visualIndex(logico)

                    if visual_atual != visual_destino:

                        header.moveSection(
                            visual_atual,
                            visual_destino
                        )

            larguras = configuracao.get("larguras", {})

            for coluna, largura in larguras.items():

                coluna = int(coluna)

                if 0 <= coluna < self.tabela.columnCount():

                    self.tabela.setColumnWidth(
                        coluna,
                        int(largura)
                    )

            ocultas = configuracao.get("ocultas", [])

            for coluna in ocultas:

                coluna = int(coluna)

                if 0 <= coluna < self.tabela.columnCount():

                    self.tabela.setColumnHidden(
                        coluna,
                        True
                    )

            alinhamentos = configuracao.get("alinhamentos", {})

            self.alinhamento_colunas.clear()

            for coluna, alinhamento in alinhamentos.items():

                coluna = int(coluna)

                if 0 <= coluna < self.tabela.columnCount():

                    self.alinhamento_colunas[coluna] = (
                        Qt.AlignmentFlag(int(alinhamento))
                    )

            fixadas = configuracao.get("fixadas", [])

            self.colunas_fixadas.clear()

            for coluna in fixadas:

                coluna = int(coluna)

                if 0 <= coluna < self.tabela.columnCount():

                    largura = self.tabela.columnWidth(coluna)

                    header.setSectionResizeMode(
                        coluna,
                        QHeaderView.Fixed
                    )

                    self.tabela.setColumnWidth(
                        coluna,
                        largura
                    )

                    self.colunas_fixadas.add(coluna)

        except Exception:

            self.aplicar_ordem_padrao()

        # ========================================================
    # MENU CABEÇALHO
    # ========================================================

    def abrir_menu_coluna_direito(
        self,
        posicao
    ):

        header = self.tabela.horizontalHeader()

        coluna = header.logicalIndexAt(
            posicao
        )

        if coluna < 0 or coluna >= self.tabela.columnCount():
            return

        self.coluna_selecionada = coluna

        self.abrir_menu_coluna(
            posicao_global=header.mapToGlobal(
                posicao
            )
        )

    # ========================================================
    # MENU CÉLULA
    # ========================================================

    def abrir_menu_coluna_celula(
        self,
        posicao
    ):

        coluna = self.tabela.columnAt(
            posicao.x()
        )

        if coluna < 0 or coluna >= self.tabela.columnCount():
            return

        self.coluna_selecionada = coluna

        self.abrir_menu_coluna(
            posicao_global=self.tabela.mapToGlobal(
                posicao
            )
        )

    # ========================================================
    # SELEÇÃO
    # ========================================================

    def alternar_modo_selecao(
        self,
        estado
    ):

        ativo = bool(estado)

        if not ativo:
            # Ao desmarcar, remove imediatamente todas as marcações.
            for linha, coluna in list(self._celulas_selecionadas):
                self._pintar_celula_selecionada(
                    linha,
                    coluna,
                    False
                )

            self._celulas_selecionadas.clear()
            self.tabela.clearSelection()

    def alternar_selecao_celula(
        self,
        linha,
        coluna
    ):

        # Fora do modo Selecionar, mantém exatamente o comportamento
        # normal da tabela.
        if not self.chkSelecionar.isChecked():
            return

        chave = (linha, coluna)

        if chave in self._celulas_selecionadas:
            self._celulas_selecionadas.remove(chave)
            selecionada = False
        else:
            self._celulas_selecionadas.add(chave)
            selecionada = True

        self._pintar_celula_selecionada(
            linha,
            coluna,
            selecionada
        )

        # Não deixa o destaque padrão azul da seleção do Qt esconder
        # a marcação laranja.
        self.tabela.clearSelection()

    def _pintar_celula_selecionada(
        self,
        linha,
        coluna,
        selecionada
    ):

        if (
            linha < 0
            or linha >= self.tabela.rowCount()
            or coluna < 0
            or coluna >= self.tabela.columnCount()
        ):
            return

        cor = QColor(
            255,
            165,
            0
        ) if selecionada else QColor(
            255,
            255,
            255
        )

        item = self.tabela.item(
            linha,
            coluna
        )

        if item is not None:
            item.setBackground(
                cor
            )

        # A coluna Descricao XML usa QLabel como widget da célula.
        # Nesse caso, a cor precisa ser aplicada diretamente ao QLabel.
        widget = self.tabela.cellWidget(
            linha,
            coluna
        )

        if widget is not None:
            if selecionada:
                widget.setStyleSheet(
                    """
                    QLabel {
                        background-color: rgb(255, 165, 0);
                        color: black;
                        padding: 2px;
                    }
                    """
                )
            else:
                widget.setStyleSheet(
                    """
                    QLabel {
                        background-color: transparent;
                        color: black;
                        padding: 2px;
                    }
                    """
                )

    def limpar_selecoes_manuais(self):

        for linha, coluna in list(
            self._celulas_selecionadas
        ):
            self._pintar_celula_selecionada(
                linha,
                coluna,
                False
            )

        self._celulas_selecionadas.clear()

    # ========================================================
    # SELEÇÃO
    # ========================================================

    def selecionar_coluna(
        self,
        linha,
        coluna
    ):

        self.coluna_selecionada = coluna

    def selecionar_coluna_header(
        self,
        coluna
    ):

        self.coluna_selecionada = coluna

    def obter_coluna_selecionada(self):

        coluna = self.coluna_selecionada

        if (
            coluna < 0
            or coluna >= self.tabela.columnCount()
        ):

            coluna = self.tabela.currentColumn()

        if (
            coluna < 0
            or coluna >= self.tabela.columnCount()
        ):

            QMessageBox.information(
                self,
                "Coluna",
                "Clique primeiro em uma coluna da tabela."
            )

            return -1

        self.coluna_selecionada = coluna

        return coluna

    # ========================================================
    # CRIAR AÇÃO
    # ========================================================

    def criar_acao_coluna(
        self,
        menu,
        texto,
        funcao
    ):

        acao = QAction(
            texto,
            self
        )

        acao.triggered.connect(
            funcao
        )

        menu.addAction(
            acao
        )

        return acao

    # ========================================================
    # MENU COLUNA
    # ========================================================

    def abrir_menu_coluna(
        self,
        posicao_global=None
    ):

        coluna = self.obter_coluna_selecionada()

        if coluna < 0:
            return

        menu = QMenu(
            self
        )

        menu.setStyleSheet(
            """
            QMenu {
                background-color: white;
                color: #111111;
                border: 1px solid #cccccc;
                padding: 4px;
            }

            QMenu::item {
                padding: 7px 22px 7px 22px;
                border-radius: 4px;
            }

            QMenu::item:selected {
                background-color: #dcecff;
                color: #0b3d91;
            }
            """
        )

        self.criar_acao_coluna(
            menu,
            "Expandir",
            self.coluna_expandir
        )

        self.criar_acao_coluna(
            menu,
            "Reduzir",
            self.coluna_reduzir
        )

        menu.addSeparator()

        self.criar_acao_coluna(
            menu,
            "Mover para esquerda",
            self.coluna_mover_esquerda
        )

        self.criar_acao_coluna(
            menu,
            "Mover para direita",
            self.coluna_mover_direita
        )

        menu.addSeparator()

        self.criar_acao_coluna(
            menu,
            "Apagar / Ocultar",
            self.coluna_apagar
        )

        self.criar_acao_coluna(
            menu,
            "Restaurar",
            self.coluna_restaurar
        )

        menu.addSeparator()

        self.criar_acao_coluna(
            menu,
            "Fixar",
            self.coluna_fixar
        )

        self.criar_acao_coluna(
            menu,
            "Desfixar",
            self.coluna_desfixar
        )

        self.criar_acao_coluna(
            menu,
            "Organizar / Ajustar ao conteudo",
            self.coluna_organizar
        )

        self.criar_acao_coluna(
            menu,
            "Localizar coluna",
            self.coluna_localizar
        )

        menu.addSeparator()

        self.criar_acao_coluna(
            menu,
            "Esquerda",
            self.coluna_alinhar_esquerda
        )

        self.criar_acao_coluna(
            menu,
            "Centro",
            self.coluna_alinhar_centro
        )

        self.criar_acao_coluna(
            menu,
            "Direita",
            self.coluna_alinhar_direita
        )

        menu.addSeparator()

        self.criar_acao_coluna(
            menu,
            "Crescente",
            self.coluna_ordenar_crescente
        )

        self.criar_acao_coluna(
            menu,
            "Decrescente",
            self.coluna_ordenar_decrescente
        )

        if posicao_global is None:

            posicao_global = (
                self.btColuna.mapToGlobal(
                    self.btColuna.rect().bottomLeft()
                )
            )

        menu.exec(
            posicao_global
        )

    # ========================================================
    # EXPANDIR
    # ========================================================

    def coluna_expandir(self):

        coluna = self.obter_coluna_selecionada()

        if coluna < 0:
            return

        largura = self.tabela.columnWidth(
            coluna
        )

        self.tabela.setColumnWidth(
            coluna,
            largura + 30
        )

    # ========================================================
    # REDUZIR
    # ========================================================

    def coluna_reduzir(self):

        coluna = self.obter_coluna_selecionada()

        if coluna < 0:
            return

        largura = self.tabela.columnWidth(
            coluna
        )

        self.tabela.setColumnWidth(
            coluna,
            max(
                40,
                largura - 30
            )
        )

    # ========================================================
    # MOVER ESQUERDA
    # ========================================================

    def coluna_mover_esquerda(self):

        coluna = self.obter_coluna_selecionada()

        if coluna < 0:
            return

        header = self.tabela.horizontalHeader()

        visual = header.visualIndex(
            coluna
        )

        if visual <= 0:
            return

        header.moveSection(
            visual,
            visual - 1
        )

    # ========================================================
    # MOVER DIREITA
    # ========================================================

    def coluna_mover_direita(self):

        coluna = self.obter_coluna_selecionada()

        if coluna < 0:
            return

        header = self.tabela.horizontalHeader()

        visual = header.visualIndex(
            coluna
        )

        ultimo = (
            self.tabela.columnCount()
            - 1
        )

        if visual >= ultimo:
            return

        header.moveSection(
            visual,
            visual + 1
        )

    # ========================================================
    # OCULTAR
    # ========================================================

    def coluna_apagar(self):

        coluna = self.obter_coluna_selecionada()

        if coluna < 0:
            return

        self.tabela.setColumnHidden(
            coluna,
            True
        )

    # ========================================================
    # RESTAURAR
    # ========================================================

    def coluna_restaurar(self):

        header = self.tabela.horizontalHeader()

        for coluna in range(
            self.tabela.columnCount()
        ):

            self.tabela.setColumnHidden(
                coluna,
                False
            )

        for visual_destino, logico in enumerate(
            self._ordem_colunas_original
        ):

            visual_atual = header.visualIndex(
                logico
            )

            if visual_atual != visual_destino:

                header.moveSection(
                    visual_atual,
                    visual_destino
                )

        for coluna, largura in (
            self._larguras_colunas_original.items()
        ):

            self.tabela.setColumnWidth(
                coluna,
                largura
            )

        for coluna in list(
            self.colunas_fixadas
        ):

            header.setSectionResizeMode(
                coluna,
                QHeaderView.Interactive
            )

        self.colunas_fixadas.clear()

        self.alinhamento_colunas.clear()

        self.preencher(
            self.produtos_filtrados_atual()
        )

    # ========================================================
    # FIXAR
    # ========================================================

    def coluna_fixar(self):

        coluna = self.obter_coluna_selecionada()

        if coluna < 0:
            return

        header = self.tabela.horizontalHeader()

        largura = self.tabela.columnWidth(
            coluna
        )

        header.setSectionResizeMode(
            coluna,
            QHeaderView.Fixed
        )

        self.tabela.setColumnWidth(
            coluna,
            largura
        )

        self.colunas_fixadas.add(
            coluna
        )

    # ========================================================
    # DESFIXAR
    # ========================================================

    def coluna_desfixar(self):

        coluna = self.obter_coluna_selecionada()

        if coluna < 0:
            return

        self.tabela.horizontalHeader().setSectionResizeMode(
            coluna,
            QHeaderView.Interactive
        )

        self.colunas_fixadas.discard(
            coluna
        )

    # ========================================================
    # ORGANIZAR
    # ========================================================

    def coluna_organizar(self):

        coluna = self.obter_coluna_selecionada()

        if coluna < 0:
            return

        self.tabela.resizeColumnToContents(
            coluna
        )

        self.tabela.setColumnWidth(
            coluna,
            max(
                40,
                self.tabela.columnWidth(
                    coluna
                )
            )
        )

    # ========================================================
    # LOCALIZAR
    # ========================================================

    def coluna_localizar(self):

        coluna = self.obter_coluna_selecionada()

        if coluna < 0:
            return

        if self.tabela.isColumnHidden(
            coluna
        ):

            self.tabela.setColumnHidden(
                coluna,
                False
            )

        linha = self.tabela.currentRow()

        if (
            linha < 0
            and self.tabela.rowCount() > 0
        ):

            linha = 0

        if linha >= 0:

            item = self.tabela.item(
                linha,
                coluna
            )

            if item is not None:

                self.tabela.scrollToItem(
                    item,
                    QTableWidget.PositionAtCenter
                )

            self.tabela.setCurrentCell(
                linha,
                coluna
            )

    # ========================================================
    # ALINHAMENTO
    # ========================================================

    def definir_alinhamento_coluna(
        self,
        coluna,
        alinhamento
    ):

        if coluna < 0:
            return

        self.alinhamento_colunas[
            coluna
        ] = alinhamento

        for linha in range(
            self.tabela.rowCount()
        ):

            item = self.tabela.item(
                linha,
                coluna
            )

            if item is not None:

                item.setTextAlignment(
                    alinhamento
                )

            widget = self.tabela.cellWidget(
                linha,
                coluna
            )

            if isinstance(
                widget,
                QLabel
            ):

                widget.setAlignment(
                    alinhamento
                )

    def coluna_alinhar_esquerda(self):

        coluna = self.obter_coluna_selecionada()

        if coluna >= 0:

            self.definir_alinhamento_coluna(
                coluna,
                Qt.AlignLeft | Qt.AlignVCenter
            )

    def coluna_alinhar_centro(self):

        coluna = self.obter_coluna_selecionada()

        if coluna >= 0:

            self.definir_alinhamento_coluna(
                coluna,
                Qt.AlignCenter
            )

    def coluna_alinhar_direita(self):

        coluna = self.obter_coluna_selecionada()

        if coluna >= 0:

            self.definir_alinhamento_coluna(
                coluna,
                Qt.AlignRight | Qt.AlignVCenter
            )

    # ========================================================
    # ORDENAÇÃO
    # ========================================================

    def coluna_ordenar(
        self,
        ordem
    ):

        coluna = self.obter_coluna_selecionada()

        if coluna < 0:
            return

        self.tabela.setSortingEnabled(
            True
        )

        self.tabela.sortItems(
            coluna,
            ordem
        )

        self.tabela.setSortingEnabled(
            False
        )

    def coluna_ordenar_crescente(self):

        self.coluna_ordenar(
            Qt.AscendingOrder
        )

    def coluna_ordenar_decrescente(self):

        self.coluna_ordenar(
            Qt.DescendingOrder
        )

    # ========================================================
    # FILTRO
    # ========================================================

    def _interpretar_filtro_sequencia(self, texto):
        """Interpreta filtros como 1-6 ou 1-6,10-15.

        Retorna um set com as sequencias solicitadas quando o texto
        inteiro estiver no formato de sequencia. Caso contrario, retorna None
        para manter a pesquisa normal por codigo/produto/NF/chave.
        """
        texto = str(texto or "").strip()
        if not texto:
            return None

        if not re.fullmatch(
            r"\d+(?:\s*-\s*\d+)?(?:\s*,\s*\d+(?:\s*-\s*\d+)?)*",
            texto
        ):
            return None

        sequencias = set()

        try:
            for parte in texto.split(","):
                parte = parte.strip()
                if "-" in parte:
                    inicio, fim = (
                        int(x.strip())
                        for x in parte.split("-", 1)
                    )
                    if inicio > fim:
                        inicio, fim = fim, inicio
                    sequencias.update(range(inicio, fim + 1))
                else:
                    sequencias.add(int(parte))
        except (TypeError, ValueError):
            return None

        return sequencias

    def produtos_filtrados_atual(self):

        texto = (
            self.txtPesquisa.text()
            .strip()
            .lower()
        )

        filtro_sequencia = self._interpretar_filtro_sequencia(texto)

        filtro_embalagem = (
            self.txtEmbalagem.text()
            .strip()
            .lower()
        )

        somente_emb_diferente_un = (
            self.chkEmbDiferenteUN.isChecked()
        )

        lista = []

        for p in self.produtos:

            if filtro_sequencia is not None:
                seq = p.get("seq", "")
                if seq in (None, ""):
                    seq = p.get("nItem", "")

                try:
                    seq_num = int(float(str(seq).strip()))
                except (TypeError, ValueError):
                    continue

                if seq_num not in filtro_sequencia:
                    continue
            else:
                busca = (
                    str(p.get("codigo", ""))
                    + str(p.get("descricao", ""))
                    + str(p.get("emitente", ""))
                    + str(p.get("numero_nf", ""))
                    + str(self.chave_nfe)
                    + str(self.pagamento_texto)
                ).lower()

                if texto not in busca:
                    continue

            embalagem = (
                self.obter_embalagem(
                    p
                ).lower()
            )

            if (
                filtro_embalagem
                and filtro_embalagem not in embalagem
            ):
                continue

            unidade = str(
                p.get(
                    "ucom",
                    ""
                ) or ""
            ).strip().upper()

            if (
                somente_emb_diferente_un
                and unidade == "UN"
            ):
                continue

            lista.append(
                p
            )

        return lista

    def copiar_texto_label(self, label, event=None):
        """Copia para a area de transferencia o texto do campo clicado."""
        texto = str(label.text() or "").strip()
        if texto:
            QApplication.clipboard().setText(texto)

        # Mantem tambem o comportamento normal de selecao do QLabel.
        if event is not None:
            try:
                QLabel.mousePressEvent(label, event)
            except Exception:
                pass

    # ========================================================
    # CHAVE NF-E
    # ========================================================

    def obter_chave_nfe(
        self,
        arquivo
    ):

        try:

            tree = ET.parse(
                arquivo
            )

            root = tree.getroot()

            for elemento in root.iter():

                for atributo, valor in (
                    elemento.attrib.items()
                ):

                    if atributo.lower() == "id":

                        valor = str(
                            valor or ""
                        ).strip()

                        encontrado = re.search(
                            r"NFe(\d{44})",
                            valor,
                            re.IGNORECASE
                        )

                        if encontrado:
                            return encontrado.group(1)

                        encontrado = re.search(
                            r"\b(\d{44})\b",
                            valor
                        )

                        if encontrado:
                            return encontrado.group(1)

            with open(
                arquivo,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as f:

                conteudo = f.read()

            encontrado = re.search(
                r"NFe(\d{44})",
                conteudo,
                re.IGNORECASE
            )

            if encontrado:
                return encontrado.group(1)

            encontrado = re.search(
                r"\b(\d{44})\b",
                conteudo
            )

            if encontrado:
                return encontrado.group(1)

        except Exception:
            pass

        return ""

    # ========================================================
    # SEQ
    # ========================================================

    def obter_seq_xml(
        self,
        arquivo
    ):

        sequencias = []

        try:

            tree = ET.parse(
                arquivo
            )

            root = tree.getroot()

            for elemento in root.iter():

                nome = (
                    elemento.tag
                    .split("}")[-1]
                    .lower()
                )

                if nome != "det":
                    continue

                seq = elemento.attrib.get(
                    "nItem",
                    ""
                )

                if not seq:

                    seq = elemento.attrib.get(
                        "seq",
                        ""
                    )

                if seq:

                    sequencias.append(
                        str(seq).strip()
                    )

        except Exception:
            pass

        return sequencias

    # ========================================================
    # ASSOCIAR SEQ
    # ========================================================

    def associar_seq_produtos(
        self,
        produtos,
        arquivo
    ):

        sequencias = self.obter_seq_xml(
            arquivo
        )

        for indice, produto in enumerate(
            produtos
        ):

            seq_existente = produto.get(
                "seq",
                ""
            )

            if seq_existente not in (
                None,
                ""
            ):
                continue

            seq_existente = produto.get(
                "nItem",
                ""
            )

            if seq_existente not in (
                None,
                ""
            ):

                produto["seq"] = str(
                    seq_existente
                )

                continue

            if indice < len(
                sequencias
            ):

                produto["seq"] = (
                    sequencias[indice]
                )

            else:

                produto["seq"] = str(
                    indice + 1
                )

    # ========================================================
    # PAGAMENTO
    # ========================================================

    def obter_formas_pagamento(
        self,
        arquivo
    ):

        formas = []

        mapa_pagamento = {
            "01": "Dinheiro",
            "02": "Cheque",
            "03": "Cartao de Credito",
            "04": "Cartao de Debito",
            "05": "Credito Loja",
            "10": "Vale Alimentacao",
            "11": "Vale Refeicao",
            "12": "Vale Presente",
            "13": "Vale Combustivel",
            "14": "Duplicata Mercantil",
            "15": "Boleto Bancario",
            "16": "Deposito Bancario",
            "17": "PIX",
            "18": "Transferencia Bancaria",
            "19": "Programa de Fidelidade",
            "90": "Sem Pagamento",
            "99": "Outros",
        }

        try:

            tree = ET.parse(
                arquivo
            )

            root = tree.getroot()

            pagamentos_xml = []

            for elemento in root.iter():

                nome = (
                    elemento.tag
                    .split("}")[-1]
                    .lower()
                )

                if nome == "detpag":

                    pagamentos_xml.append(
                        elemento
                    )

            duplicatas = []

            for elemento in root.iter():

                nome = (
                    elemento.tag
                    .split("}")[-1]
                    .lower()
                )

                if nome == "dup":

                    dados_dup = {
                        "numero": "",
                        "vencimento": "",
                        "valor": "",
                    }

                    for filho in elemento:

                        nome_filho = (
                            filho.tag
                            .split("}")[-1]
                            .lower()
                        )

                        texto = str(
                            filho.text or ""
                        ).strip()

                        if nome_filho == "ndup":

                            dados_dup[
                                "numero"
                            ] = texto

                        elif nome_filho == "dvenc":

                            dados_dup[
                                "vencimento"
                            ] = texto

                        elif nome_filho == "vdup":

                            dados_dup[
                                "valor"
                            ] = texto

                    duplicatas.append(
                        dados_dup
                    )

            forma_principal = (
                "Nao informado"
            )

            pagamentos_detalhados = []

            for det_pag in pagamentos_xml:

                codigo = ""

                valor_pagamento = ""

                for filho in det_pag:

                    nome = (
                        filho.tag
                        .split("}")[-1]
                        .lower()
                    )

                    texto = str(
                        filho.text or ""
                    ).strip()

                    if nome == "tpag":

                        codigo = texto

                    elif nome == "vpag":

                        valor_pagamento = texto

                descricao = mapa_pagamento.get(
                    codigo,
                    (
                        f"Codigo {codigo}"
                        if codigo
                        else "Nao informado"
                    )
                )

                if forma_principal == "Nao informado":

                    forma_principal = descricao

                pagamentos_detalhados.append({
                    "descricao": descricao,
                    "valor": valor_pagamento,
                })

            if duplicatas:

                total_parcelas = len(
                    duplicatas
                )

                for indice, duplicata in enumerate(
                    duplicatas,
                    start=1
                ):

                    numero = duplicata.get(
                        "numero",
                        ""
                    )

                    if not numero:

                        numero = (
                            f"{indice:03d}"
                        )

                    vencimento = duplicata.get(
                        "vencimento",
                        ""
                    )

                    valor = duplicata.get(
                        "valor",
                        ""
                    )

                    if re.match(
                        r"^\d{4}-\d{2}-\d{2}$",
                        vencimento
                    ):

                        ano = vencimento[0:4]
                        mes = vencimento[5:7]
                        dia = vencimento[8:10]

                        vencimento = (
                            f"{dia}/{mes}/{ano}"
                        )

                    valor_formatado = ""

                    if valor:

                        try:

                            valor_float = float(
                                valor.replace(
                                    ",",
                                    "."
                                )
                            )

                            valor_formatado = (
                                f"R$ {valor_float:,.2f}"
                                .replace(",", "X")
                                .replace(".", ",")
                                .replace("X", ".")
                            )

                        except Exception:

                            valor_formatado = valor

                    texto_parcela = (
                        f"{forma_principal} - "
                        f"Parcela "
                        f"{numero}/"
                        f"{total_parcelas}"
                    )

                    if vencimento:

                        texto_parcela += (
                            f" - Venc: "
                            f"{vencimento}"
                        )

                    if valor_formatado:

                        texto_parcela += (
                            f" - "
                            f"{valor_formatado}"
                        )

                    formas.append(
                        texto_parcela
                    )

            elif pagamentos_detalhados:

                for pagamento in (
                    pagamentos_detalhados
                ):

                    descricao = pagamento.get(
                        "descricao",
                        "Nao informado"
                    )

                    valor = pagamento.get(
                        "valor",
                        ""
                    )

                    if valor:

                        try:

                            valor_float = float(
                                valor.replace(
                                    ",",
                                    "."
                                )
                            )

                            valor_formatado = (
                                f"R$ {valor_float:,.2f}"
                                .replace(",", "X")
                                .replace(".", ",")
                                .replace("X", ".")
                            )

                            descricao = (
                                f"{descricao} - "
                                f"{valor_formatado}"
                            )

                        except Exception:
                            pass

                    formas.append(
                        descricao
                    )

            if not formas:

                formas.append(
                    "Nao informado"
                )

            formas_sem_duplicados = []

            for forma in formas:

                if forma not in (
                    formas_sem_duplicados
                ):

                    formas_sem_duplicados.append(
                        forma
                    )

            return formas_sem_duplicados

        except Exception:

            return []

    # ========================================================
    # CHAVE NA TELA
    # ========================================================

    def atualizar_chave_tela(
        self,
        chave
    ):

        self.chave_nfe = str(
            chave or ""
        )

        if self.chave_nfe:

            self.txtChave.setText(
                self.chave_nfe
            )

        else:

            self.txtChave.setText(
                "Nao encontrada"
            )

    # ========================================================
    # PAGAMENTO NA TELA
    # ========================================================

    def atualizar_pagamento_tela(
        self,
        formas
    ):

        self.formas_pagamento = list(
            formas or []
        )

        if self.formas_pagamento:

            self.pagamento_texto = (
                " | ".join(
                    self.formas_pagamento
                )
            )

            # Mantém o texto original para mensagens e outras rotinas.
            # Na tela, somente o valor recebe fundo vermelho e a data
            # de vencimento recebe fundo amarelo.
            partes_html = []

            for forma in self.formas_pagamento:

                texto_html = _html.escape(
                    str(forma)
                )

                # Valor da parcela: somente "R$ ..." fica com fundo vermelho.
                texto_html = re.sub(
                    r"(R\$\s*[0-9.]+,[0-9]{2})",
                    (
                        r'<span style="background-color:#ff0000;'
                        r' color:#ffffff; padding:2px 4px; '
                        r'border-radius:2px; font-weight:bold;">\1</span>'
                    ),
                    texto_html,
                    flags=re.IGNORECASE
                )

                # Data de vencimento: somente a data fica com fundo amarelo.
                texto_html = re.sub(
                    r"(Venc:\s*)([0-9]{2}/[0-9]{2}/[0-9]{4})",
                    (
                        r'\1<span style="background-color:#ffff00;'
                        r' color:#000000; padding:2px 4px; '
                        r'border-radius:2px; font-weight:bold;">\2</span>'
                    ),
                    texto_html,
                    flags=re.IGNORECASE
                )

                partes_html.append(
                    texto_html
                )

            self.txtPagamento.setText(
                " <span style=\"color:#555555;\">|</span> ".join(
                    partes_html
                )
            )

        else:

            self.pagamento_texto = ""

            self.txtPagamento.setText(
                "Nao informado"
            )

    # ========================================================
    # PDF -> XML
    # ========================================================

    def abrir_pdf(self):

        arquivo, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar PDF ou XML",
            "",
            "Arquivos PDF ou XML (*.pdf *.xml);;"
            "Arquivos PDF (*.pdf);;"
            "Arquivos XML (*.xml)"
        )

        if not arquivo:
            return

        try:

            extensao = os.path.splitext(
                arquivo
            )[1].lower()

            if extensao == ".xml":

                self.btAbrir.setEnabled(
                    False
                )

                self.btAbrir.setText(
                    "Lendo XML..."
                )

                QApplication.processEvents()

                self.carregar_xml(
                    arquivo,
                    mostrar_sucesso=False
                )

                return

            if extensao == ".pdf":

                # Acrescenta o nome usado no proprio arquivo PDF.
                # Ex.: "DALLAS.pdf" -> "FORN: DALLAS".
                # O fornecedor vindo do XML continua intacto.
                nome_fornecedor_pdf = os.path.splitext(
                    os.path.basename(arquivo)
                )[0].strip()

                self.lblFornArquivo.setText(
                    f"FORN: {nome_fornecedor_pdf}"
                )

                self.btAbrir.setEnabled(
                    False
                )

                self.btAbrir.setText(
                    "Baixando XML..."
                )

                QApplication.processEvents()

                caminho_xml = baixar_xml_do_pdf(
                    arquivo
                )

                if not caminho_xml:
                    raise Exception(
                        "A rotina nao retornou o caminho do XML."
                    )

                if not os.path.exists(
                    caminho_xml
                ):
                    raise Exception(
                        "O XML foi baixado, mas o arquivo nao foi encontrado."
                    )

                self.btAbrir.setText(
                    "Lendo XML..."
                )

                QApplication.processEvents()

                self.carregar_xml(
                    caminho_xml,
                    mostrar_sucesso=True
                )

                return

            raise Exception(
                "Selecione um arquivo PDF ou XML."
            )

        except Exception as erro:

            QMessageBox.critical(
                self,
                "Erro",
                str(erro)
            )

        finally:

            self.btAbrir.setEnabled(
                True
            )

            self.btAbrir.setText(
                "Abrir PDF / Baixar XML"
            )

    # ========================================================
    # ABRIR XML
    # ========================================================

    def abrir_xml(self):

        arquivo, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir XML",
            "",
            "Arquivos XML (*.xml)"
        )

        if not arquivo:
            return

        self.carregar_xml(
            arquivo
        )

    # ========================================================
    # CARREGAR XML
    # ========================================================

    def carregar_xml(
        self,
        arquivo,
        mostrar_sucesso=False
    ):

        try:

            leitor = LeitorXML(
                arquivo
            )

            nota = leitor.ler()

            self.produtos = nota[
                "produtos"
            ]

            self.associar_seq_produtos(
                self.produtos,
                arquivo
            )

            chave = self.obter_chave_nfe(
                arquivo
            )

            self.atualizar_chave_tela(
                chave
            )

            formas_pagamento = (
                self.obter_formas_pagamento(
                    arquivo
                )
            )

            self.atualizar_pagamento_tela(
                formas_pagamento
            )

            self.lblFornecedor.setText(
                f"Fornecedor: "
                f"{nota['emitente']}"
            )

            self.lblNF.setText(
                f"NF: "
                f"{nota['numero']}"
            )

            self.atualizar_resumo()

            self.filtrar()

            if mostrar_sucesso:

                chave_texto = (
                    self.chave_nfe
                    if self.chave_nfe
                    else "Nao encontrada"
                )

                pagamento_texto = (
                    self.pagamento_texto
                    if self.pagamento_texto
                    else "Nao informado"
                )

                QMessageBox.information(
                    self,
                    "XML baixado",
                    (
                        "NF-e carregada com sucesso!\n\n"
                        f"Fornecedor: "
                        f"{nota['emitente']}\n"
                        f"NF: "
                        f"{nota['numero']}\n"
                        f"Chave NF-e: "
                        f"{chave_texto}\n"
                        f"Forma de Pagamento: "
                        f"{pagamento_texto}\n"
                        f"Produtos: "
                        f"{len(self.produtos)}\n\n"
                        f"XML salvo em:\n"
                        f"{arquivo}"
                    )
                )

        except Exception as erro:

            QMessageBox.critical(
                self,
                "Erro",
                str(erro)
            )

    # ========================================================
    # ABRIR PASTA XML
    # ========================================================

    def abrir_pasta(self):

        pasta = QFileDialog.getExistingDirectory(
            self,
            "Selecionar pasta com XML"
        )

        if not pasta:
            return

        produtos = []

        total_xml = 0

        chaves = []

        pagamentos = []

        for arquivo in os.listdir(
            pasta
        ):

            if not arquivo.lower().endswith(
                ".xml"
            ):
                continue

            caminho = os.path.join(
                pasta,
                arquivo
            )

            try:

                leitor = LeitorXML(
                    caminho
                )

                nota = leitor.ler()

                produtos_nota = nota[
                    "produtos"
                ]

                self.associar_seq_produtos(
                    produtos_nota,
                    caminho
                )

                produtos.extend(
                    produtos_nota
                )

                chave = self.obter_chave_nfe(
                    caminho
                )

                if chave:

                    chaves.append(
                        chave
                    )

                formas = (
                    self.obter_formas_pagamento(
                        caminho
                    )
                )

                pagamentos.extend(
                    formas
                )

                total_xml += 1

            except Exception:
                pass

        if not produtos:

            QMessageBox.warning(
                self,
                "Aviso",
                "Nenhum produto encontrado."
            )

            return

        self.produtos = produtos

        self.lblFornecedor.setText(
            "Fornecedor: Varios"
        )

        self.lblNF.setText(
            f"XML processados: "
            f"{total_xml}"
        )

        if len(chaves) == 1:

            self.atualizar_chave_tela(
                chaves[0]
            )

        elif len(chaves) > 1:

            self.chave_nfe = ""

            self.txtChave.setText(
                f"{len(chaves)} notas carregadas"
            )

        else:

            self.atualizar_chave_tela(
                ""
            )

        pagamentos_sem_duplicados = []

        for pagamento in pagamentos:

            if pagamento not in (
                pagamentos_sem_duplicados
            ):

                pagamentos_sem_duplicados.append(
                    pagamento
                )

        self.atualizar_pagamento_tela(
            pagamentos_sem_duplicados
        )

        self.atualizar_resumo()

        self.filtrar()

    # ========================================================
    # RESUMO
    # ========================================================

    def atualizar_resumo(self):

        total = len(
            self.produtos
        )

        self.lblQtd.setText(
            f"Produtos: {total}"
        )

    # ========================================================
    # EMBALAGEM
    # ========================================================

    def obter_embalagem(
        self,
        produto
    ):

        qcom = float(
            produto.get(
                "qcom",
                0
            ) or 0
        )

        ucom = str(
            produto.get(
                "ucom",
                ""
            ) or ""
        ).strip()

        return (
            f"{qcom:g} {ucom}"
        ).strip()

    # ========================================================
    # FILTRO
    # ========================================================

    def filtrar(self):

        lista = (
            self.produtos_filtrados_atual()
        )

        self.preencher(
            lista
        )

    # ========================================================
    # MULTIPLICADOR
    # ========================================================

    def calcular_multiplicador(
        self,
        descricao,
        compra
    ):

        descricao = str(
            descricao or ""
        )

        compra = str(
            compra or ""
        )

        if re.search(
            r"\bUN\b",
            compra,
            re.IGNORECASE
        ):

            return 1

        encontrados_x = re.findall(
            r'(\d+(?:[.,]\d+)?)\s*[Xx]\s*'
            r'\d+(?:[.,]\d+)?',
            descricao,
            re.IGNORECASE
        )

        if encontrados_x:

            return float(
                encontrados_x[0].replace(
                    ",",
                    "."
                )
            )

        encontrados_cx = re.findall(
            r'\b(?:CX|CAIXA)\s*'
            r'(\d+(?:[.,]\d+)?)\b',
            descricao,
            re.IGNORECASE
        )

        if encontrados_cx:

            return float(
                encontrados_cx[0].replace(
                    ",",
                    "."
                )
            )

        return 1

    # ========================================================
    # FORMATAR DESCRIÇÃO
    # ========================================================

    def formatar_descricao(
        self,
        descricao
    ):

        descricao = str(
            descricao or ""
        )

        padrao = re.compile(
            r'(\d+(?:[.,]\d+)?\s*[Xx]\s*'
            r'\d+(?:[.,]\d+)?|'
            r'\b(?:CX|CAIXA)\s*'
            r'\d+(?:[.,]\d+)?)',
            re.IGNORECASE
        )

        partes = padrao.split(
            descricao
        )

        texto_formatado = ""

        for parte in partes:

            if not parte:
                continue

            if padrao.fullmatch(
                parte
            ):

                texto_formatado += (
                    '<span style="'
                    'color: blue; '
                    'font-weight: bold;">'
                    + parte
                    + '</span>'
                )

            else:

                texto_formatado += (
                    parte
                    .replace(
                        "&",
                        "&amp;"
                    )
                    .replace(
                        "<",
                        "&lt;"
                    )
                    .replace(
                        ">",
                        "&gt;"
                    )
                )

        return texto_formatado

    # ========================================================
    # VALOR UNITÁRIO XML
    # ========================================================

    def obter_valor_un_xml(
        self,
        produto
    ):

        valor = produto.get(
            "valor_unitario_xml"
        )

        if valor in (
            None,
            ""
        ):

            valor = produto.get(
                "valor_un"
            )

        if valor in (
            None,
            ""
        ):

            valor = produto.get(
                "valor_unitario"
            )

        if valor in (
            None,
            ""
        ):

            valor = produto.get(
                "vUnCom"
            )

        if valor in (
            None,
            ""
        ):

            valor = produto.get(
                "vUnTrib"
            )

        try:

            return float(
                str(
                    valor or 0
                ).replace(
                    ",",
                    "."
                )
            )

        except Exception:

            return 0

    # ========================================================
    # CALCULO
    # ========================================================

    def calcular_valor_dividido_valor_un_xml(
        self,
        valor,
        valor_un_xml
    ):

        try:

            valor = float(
                valor or 0
            )

            valor_un_xml = float(
                valor_un_xml or 0
            )

            if valor_un_xml == 0:

                return 0

            return (
                valor
                /
                valor_un_xml
            )

        except Exception:

            return 0

    # ========================================================
    # EMBALAGEM - BASE LOCAL
    # ========================================================

    def obter_texto_qtd_embalagem(self, ean, embalagem=""):
        ean = _normalizar_ean(ean)
        if not ean:
            return ""

        # Primeiro verifica a base local para TODOS os EANs.
        # Isso evita ignorar um GTIN de caixa só porque o XML informou UN.
        dados = obter_embalagem_local(
            self._base_embalagens,
            ean
        )

        if dados:
            return str(dados["quantidade"])

        # Sem cadastro local, não assume que UN = 1.
        # A quantidade da caixa deve ser obtida pela pesquisa do EAN.
        return "Não cadastrado"

    def iniciar_pesquisa_qtd_embalagem(self, ean):
        ean = _normalizar_ean(ean)
        if not ean:
            return

        for worker in self._workers_qtd_embalagem:
            if getattr(worker, "ean", "") == ean:
                return

        self._iniciar_worker_qtd_embalagem(ean)

    def _remover_worker_qtd_embalagem(self, worker):
        try:
            self._workers_qtd_embalagem.remove(worker)
        except ValueError:
            pass

    def pesquisar_ean_selecionado(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            QMessageBox.information(
                self,
                "Pesquisar EAN",
                "Selecione uma linha da tabela primeiro."
            )
            return

        item_ean = self.tabela.item(linha, 17)
        if item_ean is None:
            QMessageBox.information(
                self,
                "Pesquisar EAN",
                "A linha selecionada não possui EAN."
            )
            return

        ean = _normalizar_ean(item_ean.text())
        if not ean:
            QMessageBox.information(
                self,
                "Pesquisar EAN",
                "A linha selecionada não possui um EAN válido."
            )
            return

        if ean in self._pesquisa_lote_pendentes:
            return

        item = self.tabela.item(linha, 11)
        if item is None:
            item = QTableWidgetItem()
            self.tabela.setItem(linha, 11, item)
        item.setText("Pesquisando...")

        self.btPesquisarEAN.setEnabled(False)
        self.btPesquisarEAN.setText("Pesquisando...")
        self.iniciar_pesquisa_qtd_embalagem(ean)

    def pesquisar_eans_nao_cadastrados(self):
        """Pesquisa em paralelo somente os EANs ainda não cadastrados."""
        if self._pesquisa_lote_ativa:
            return

        eans = []
        vistos = set()

        for linha in range(self.tabela.rowCount()):
            # Coluna 15 = Cod Barras XML.
            item_ean = self.tabela.item(linha, 17)
            item_qtd = self.tabela.item(linha, 11)
            if item_ean is None:
                continue

            ean = _normalizar_ean(item_ean.text())
            if not ean or ean in vistos:
                continue

            texto_qtd = item_qtd.text().strip().lower() if item_qtd else ""
            embalagem = self.tabela.item(linha, 9)
            emb = embalagem.text().strip().upper() if embalagem else ""

            # Se já existe um resultado salvo localmente, não pesquisa novamente.
            if obter_embalagem_local(self._base_embalagens, ean):
                continue

            # UN é tratado como 1 durante o preenchimento da tabela.
            # Não enviamos UN para pesquisa automática em lote para evitar
            # transformar uma unidade simples em um resultado incerto.
            if emb in ("UN", "UND", "UNID", "UNIDADE") and texto_qtd == "1":
                continue

            if texto_qtd not in ("não cadastrado", "nao cadastrado", "não encontrado", "nao encontrado", "", "consultando..."):
                continue

            vistos.add(ean)
            eans.append(ean)

        if not eans:
            QMessageBox.information(
                self,
                "Pesquisa de EANs",
                "Não há EANs não cadastrados para pesquisar."
            )
            return

        self._pesquisa_lote_ativa = True
        self._pesquisa_lote_pendentes = set(eans)
        self._pesquisa_lote_total = len(eans)
        self._pesquisa_lote_concluidos = 0

        self.btPesquisarEAN.setEnabled(False)
        self.btPesquisarNaoCadastrados.setEnabled(False)
        self.btPesquisarNaoCadastrados.setText(
            f"Pesquisando 0/{len(eans)}..."
        )

        for linha in range(self.tabela.rowCount()):
            # Coluna 15 = Cod Barras XML.
            item_ean = self.tabela.item(linha, 17)
            if item_ean is None:
                continue
            ean = _normalizar_ean(item_ean.text())
            if ean in self._pesquisa_lote_pendentes:
                item = self.tabela.item(linha, 11)
                if item is None:
                    item = QTableWidgetItem()
                    self.tabela.setItem(linha, 11, item)
                item.setText("Pesquisando...")

        # O QThreadPool usa os workers simultaneamente.
        # Limitar a 8 evita sobrecarregar a internet.
        self._pool_qtd_embalagem.setMaxThreadCount(8)
        for ean in eans:
            self._iniciar_worker_qtd_embalagem(ean)

    def pesquisar_qtd_embalagem_automaticamente(self):
        """Pesquisa automaticamente a quantidade por embalagem de cada EAN.

        Esta rotina mexe somente na coluna Qtd/Emb. (9). A coluna QUANT (8)
        permanece exclusivamente com qCom/qTrib do XML.
        """
        eans = set()

        for linha in range(self.tabela.rowCount()):
            item_ean = self.tabela.item(linha, 17)
            if item_ean is None:
                continue

            ean = _normalizar_ean(item_ean.text())
            if not ean:
                continue

            # Se já temos a informação na base local, preencherá pela rotina
            # normal e não há necessidade de consultar a internet.
            if obter_embalagem_local(self._base_embalagens, ean):
                continue

            item_qtd_emb = self.tabela.item(linha, 11)
            texto = item_qtd_emb.text().strip().lower() if item_qtd_emb else ""
            if texto not in (
                "",
                "não cadastrado",
                "nao cadastrado",
                "não encontrado",
                "nao encontrado",
            ):
                continue

            eans.add(ean)

        for ean in eans:
            for linha in range(self.tabela.rowCount()):
                item_ean = self.tabela.item(linha, 17)
                if item_ean is None or _normalizar_ean(item_ean.text()) != ean:
                    continue

                item = self.tabela.item(linha, 11)
                if item is None:
                    item = QTableWidgetItem()
                    self.tabela.setItem(linha, 11, item)
                item.setText("Pesquisando...")
                item.setToolTip("Pesquisando a quantidade por embalagem pelo EAN...")
                item.setTextAlignment(
                    Qt.AlignmentFlag(
                        int(
                            self.alinhamento_colunas.get(
                                9, Qt.AlignLeft | Qt.AlignVCenter
                            )
                        )
                    )
                )

            self.iniciar_pesquisa_qtd_embalagem(ean)

    def _iniciar_worker_qtd_embalagem(self, ean):
        worker = _PesquisaEmbalagemWorker(ean)
        worker.sinais.resultado.connect(
            self.receber_resultado_qtd_embalagem
        )
        worker.sinais.resultado.connect(
            lambda *_args, w=worker: self._remover_worker_qtd_embalagem(w)
        )
        self._workers_qtd_embalagem.append(worker)
        self._pool_qtd_embalagem.start(worker)

    def receber_resultado_qtd_embalagem(self, ean, fator, fonte):
        ean = _normalizar_ean(ean)

        if fator:
            self._base_embalagens[ean] = {
                "quantidade": int(fator),
                "fonte": fonte or "Pesquisa web",
                "ean_master": _calcular_dun14(ean, 2) or ""
            }
            salvar_base_embalagens(self._base_embalagens)

        for linha in range(self.tabela.rowCount()):
            item_ean = self.tabela.item(linha, 17)
            if item_ean is None:
                continue
            if _normalizar_ean(item_ean.text()) != ean:
                continue

            # Coluna 9 = Qtd/Emb.
            # A coluna 8 (QUANT) permanece com qCom/qTrib do XML.
            item = self.tabela.item(linha, 11)
            if item is None:
                item = QTableWidgetItem()
                self.tabela.setItem(linha, 11, item)

            if fator:
                item.setText(str(fator))
                item.setToolTip(
                    "Quantidade por embalagem.\n"
                    "Fonte: {}\n"
                    "EAN: {}".format(fonte or "Pesquisa web", ean)
                )
            else:
                item.setText("Não cadastrado")
                item.setToolTip(
                    "Não foi encontrada uma quantidade confiável.\n"
                    "Use a pesquisa novamente quando necessário."
                )

            item.setTextAlignment(
                Qt.AlignmentFlag(
                    int(
                        self.alinhamento_colunas.get(
                            9,
                            Qt.AlignLeft | Qt.AlignVCenter
                        )
                    )
                )
            )

        # Se estamos fazendo pesquisa em lote, atualiza o progresso.
        if self._pesquisa_lote_ativa and ean in self._pesquisa_lote_pendentes:
            self._pesquisa_lote_pendentes.discard(ean)
            self._pesquisa_lote_concluidos += 1
            self.btPesquisarNaoCadastrados.setText(
                f"Pesquisando {self._pesquisa_lote_concluidos}/{self._pesquisa_lote_total}..."
            )

            if not self._pesquisa_lote_pendentes:
                self._pesquisa_lote_ativa = False
                self.btPesquisarNaoCadastrados.setEnabled(True)
                self.btPesquisarNaoCadastrados.setText(
                    "Pesquisar não cadastrados"
                )
                self.btPesquisarEAN.setEnabled(True)
                self.btPesquisarEAN.setText("Pesquisar EAN")
                QApplication.processEvents()
                QMessageBox.information(
                    self,
                    "Pesquisa concluída",
                    (
                        f"Pesquisa concluída.\n\n"
                        f"EANs pesquisados: {self._pesquisa_lote_total}\n"
                        f"A base local foi atualizada."
                    )
                )
            return

        # Pesquisa individual.
        self.btPesquisarEAN.setEnabled(True)
        self.btPesquisarEAN.setText("Pesquisar EAN")

    # ========================================================
    # PREENCHER TABELA
    # ========================================================

    def preencher(
        self,
        produtos
    ):

        # As linhas da tabela serão reconstruídas, então as marcações
        # antigas não podem ser reaproveitadas em outras linhas.
        self.limpar_selecoes_manuais()
        self.tabela.clearSelection()

        self.tabela.setRowCount(
            len(produtos)
        )

        for linha, p in enumerate(
            produtos
        ):

            qcom = float(
                p.get(
                    "qcom",
                    0
                ) or 0
            )

            qtrib = float(
                p.get(
                    "qtrib",
                    0
                ) or 0
            )

            ucom = str(
                p.get(
                    "ucom",
                    ""
                ) or ""
            )

            compra = (
                f"{qcom:g} "
                f"{ucom}"
            )

            multiplicador = (
                self.calcular_multiplicador(
                    p.get(
                        "descricao",
                        ""
                    ),
                    compra
                )
            )

            qtd_ajustada = (
                qcom
                *
                multiplicador
            )

            preco_compra = float(
                p.get(
                    "preco_compra",
                    0
                ) or 0
            )

            quantidade_ultima_entrada = float(
                p.get(
                    "quantidade_ultima_entrada",
                    0
                ) or 0
            )

            preco_ultima_compra_unit = float(
                p.get(
                    "preco_ultima_compra_unit",
                    0
                ) or 0
            )

            valor = float(
                p.get(
                    "valor",
                    0
                ) or 0
            )

            valor_un_xml = (
                self.obter_valor_un_xml(
                    p
                )
            )

            valor_dividido = (
                self.calcular_valor_dividido_valor_un_xml(
                    valor,
                    valor_un_xml
                )
            )

            seq = p.get(
                "seq",
                ""
            )

            if seq in (
                None,
                ""
            ):

                seq = p.get(
                    "nItem",
                    ""
                )

            dados = [

                p.get(
                    "codigo_erp",
                    ""
                ),

                p.get(
                    "descricao_erp",
                    ""
                ),

                f"R$ {preco_compra:.2f}",

                f"{quantidade_ultima_entrada:g}",

                f"R$ {preco_ultima_compra_unit:.2f}",
                
                f"R$ {float(p.get('prun_prultcompant', 0) or 0):.2f}",

                p.get("prun_dtultcomp", ""),

                p.get(
                    "codigo",
                    ""
                ),

                p.get(
                    "descricao",
                    ""
                ),

                compra,

                f"{qcom:g}\n{qtrib:g}",

                self.obter_texto_qtd_embalagem(
                    p.get("codigo_barras", ""),
                    ucom
                ),

                f"{qtd_ajustada:g}",

                seq,

                f"R$ {valor:.2f}",

                f"R$ {valor_un_xml:.4f}",

                f"{valor_dividido:.4f}",

                p.get(
                    "codigo_barras",
                    ""
                ),
            ]

            for coluna, texto in enumerate(
                dados
            ):

                if coluna == 8:

                    texto_formatado = (
                        self.formatar_descricao(
                            texto
                        )
                    )

                    label = QLabel(
                        texto_formatado
                    )

                    label.setTextFormat(
                        Qt.RichText
                    )

                    label.setWordWrap(
                        False
                    )

                    # A QLabel deve se comportar como parte da célula
                    # normal da tabela. Ela não pode capturar o clique nem
                    # pintar um azul próprio por cima da seleção do QTableWidget.
                    label.setFocusPolicy(
                        Qt.NoFocus
                    )
                    label.setAttribute(
                        Qt.WA_TransparentForMouseEvents,
                        True
                    )

                    label.setStyleSheet(
                        """
                        QLabel {
                            background-color: transparent;
                            color: black;
                            padding: 2px;
                        }
                        """
                    )

                    label.setAlignment(
                        Qt.AlignmentFlag(
                            int(
                                self.alinhamento_colunas.get(
                                    coluna,
                                    Qt.AlignLeft
                                    | Qt.AlignVCenter
                                )
                            )
                        )
                    )

                    self.tabela.setCellWidget(
                        linha,
                        coluna,
                        label
                    )

                    continue

                item = QTableWidgetItem(
                    str(texto)
                )

                item.setForeground(
                    QColor(
                        0,
                        0,
                        0
                    )
                )

                item.setBackground(
                    QColor(
                        255,
                        255,
                        255
                    )
                )

                item.setTextAlignment(
                    Qt.AlignmentFlag(
                        int(
                            self.alinhamento_colunas.get(
                                coluna,
                                Qt.AlignLeft
                                | Qt.AlignVCenter
                            )
                        )
                    )
                )

                if coluna == 4:

                    item.setBackground(
                        QColor(
                            255,
                            150,
                            150
                        )
                    )

                if coluna == 12:

                    # MULT: azul claro
                    item.setBackground(
                        QColor(
                            173,
                            216,
                            230
                        )
                    )

                if coluna == 14:

                    item.setBackground(
                        QColor(
                            255,
                            150,
                            150
                        )
                    )

                self.tabela.setItem(
                    linha,
                    coluna,
                    item
                )

            # QUANT (coluna 8) mostra qCom e qTrib em duas linhas.
            self.tabela.setRowHeight(
                linha,
                max(40, self.tabela.rowHeight(linha))
            )

        # Pesquisa automaticamente somente a Qtd/Emb. pelo EAN.
        # A coluna QUANT (8) permanece intacta.
        self.pesquisar_qtd_embalagem_automaticamente()


# ============================================================
# INICIALIZAÇÃO
# ============================================================

def main():

    app = QApplication(
        sys.argv
    )

    # ========================================================
    # PRIMEIRA TELA:
    # SENHA
    # ========================================================

    tela_senha = TelaSenha()

    tela_senha.show()

    # ========================================================
    # O PROGRAMA SÓ TERMINA QUANDO A APLICAÇÃO FOR FECHADA
    # ========================================================

    sys.exit(
        app.exec()
    )


# ============================================================
# EXECUTAR
# ============================================================

if __name__ == "__main__":

    main()
