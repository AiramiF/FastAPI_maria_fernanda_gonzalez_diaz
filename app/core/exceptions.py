class ErrorAplicacion(Exception):
    status_code = 400

    def __init__(self, mensaje: str) -> None:
        self.mensaje = mensaje
        super().__init__(mensaje)


class NoAutenticado(ErrorAplicacion):
    status_code = 401


class Prohibido(ErrorAplicacion):
    status_code = 403


class NoEncontrado(ErrorAplicacion):
    status_code = 404


class Conflicto(ErrorAplicacion):
    status_code = 409


class ReglaNegocio(ErrorAplicacion):
    status_code = 422


class CuentaBloqueada(ErrorAplicacion):
    status_code = 423


class ArchivoNoValido(ErrorAplicacion):
    status_code = 422


class PayloadDemasiadoGrande(ErrorAplicacion):
    status_code = 413


class ServicioExternoError(ErrorAplicacion):
    status_code = 502
