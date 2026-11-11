# Vendored code

`diffuser_layerdiffuse` is not stored in this repo. Fetch it at the tested commit and apply our one-file patch (keyword arguments for diffusers 0.37):

1. Clone it into this folder:
   ```bash
   git clone https://github.com/rootonchair/diffuser_layerdiffuse.git prototype/vendor/diffuser_layerdiffuse
   ```
2. Check out the tested commit and apply the patch:
   ```bash
   cd prototype/vendor/diffuser_layerdiffuse && git checkout b4150c1ee8e48c2f9dbf1d1083b19a0c5aa83d9d && git apply ../diffuser_layerdiffuse.patch
   ```
