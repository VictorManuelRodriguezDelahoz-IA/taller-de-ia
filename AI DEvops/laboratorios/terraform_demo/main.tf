# Un modulo chiquito para ver un `terraform plan` de verdad, sin credenciales de nube.
# Los providers `local` y `random` no tocan AWS ni nada remoto: todo pasa en esta carpeta.

terraform {
  required_version = ">= 1.5"
  required_providers {
    local  = { source = "hashicorp/local", version = "~> 2.5" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

variable "entorno" {
  description = "staging o produccion"
  type        = string
  default     = "staging"
}

variable "retencion_dias" {
  description = "cuantos dias se guardan los datos"
  type        = number
  default     = 7
}

# La clave de la base: si cambia el entorno, se regenera. Eso es un reemplazo.
resource "random_password" "clave_db" {
  length  = 24
  special = true
  keepers = {
    entorno = var.entorno
  }
}

# Un archivo con datos. Si cambia el nombre, Terraform borra el viejo y crea otro.
resource "local_file" "datos_clientes" {
  filename = "${path.module}/datos/clientes-${var.entorno}.csv"
  content  = "id,nombre,plan\n1,ClickIT,enterprise\n2,Acme,basico\n"
}

# La configuracion de la app.
resource "local_file" "configuracion" {
  filename = "${path.module}/datos/app.conf"
  content  = "entorno=${var.entorno}\nretencion_dias=${var.retencion_dias}\n"
}
