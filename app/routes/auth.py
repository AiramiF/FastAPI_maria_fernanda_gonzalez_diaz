from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from ..core.rate_limit import limiter
from ..controllers import auth as auth_controller
from ..core.dependencies import CurrentUser, SessionDep, oauth2_scheme
from ..schemas.auth import PasswordCambio, TokenPair
from ..schemas.usuario import UsuarioRegistro, UsuarioRespuesta

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post(
    "/registro",
    response_model=UsuarioRespuesta,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo socio",
)
@limiter.limit("5/minute")
def registro(
    request: Request,
    datos: UsuarioRegistro,
    db: SessionDep,
) -> UsuarioRespuesta:
    return auth_controller.registrar_usuario(db, datos)


@router.post(
    "/login",
    response_model=TokenPair,
    summary="Iniciar sesión",
)
@limiter.limit("10/minute")
def login(
    request: Request,
    db: SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenPair:
    return auth_controller.login_usuario(db, form_data.username, form_data.password)


@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Renovar tokens",
)
def refresh(
    db: SessionDep,
    token: Annotated[str, Depends(oauth2_scheme)],
) -> TokenPair:
    return auth_controller.refresh_usuario(db, token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cerrar sesión",
)
def logout(db: SessionDep, usuario: CurrentUser) -> Response:
    auth_controller.logout_usuario(db, usuario)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me",
    response_model=UsuarioRespuesta,
    summary="Obtener perfil del usuario autenticado",
)
def me(usuario: CurrentUser) -> UsuarioRespuesta:
    return auth_controller.obtener_mi_perfil(usuario)


@router.patch(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cambiar contraseña del usuario autenticado",
)
def cambiar_password(
    db: SessionDep,
    usuario: CurrentUser,
    payload: PasswordCambio,
) -> Response:
    auth_controller.cambiar_password(db, usuario, payload)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
