# adding a workaround, as computed values are not supported due to id & ns validation
resource "kestra_test" "unitTest-orderItem" {
  content   = file("${path.module}/unitTest-orderItem.yaml")

  namespace = "solutions.ops"
  test_id   = "unitTest-orderItem"
}

terraform {
  required_providers {
    kestra = {
      source  = "kestra-io/kestra"
      version = "~> 1.0"
    }
  }
}