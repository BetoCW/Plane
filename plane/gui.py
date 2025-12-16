import io
import os
import shutil
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from PIL import Image, ImageTk, ImageGrab

try:
    import pytesseract
except ImportError:
    pytesseract = None

from .ocr import extract_multipliers_from_image, append_to_csv
from .fit import fit_models, best_model_by_aic
from .report import summarize_fit
from .survival import empirical_survival


class OCRGui(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Plane OCR - Multipliers")
        self.geometry("800x600")

        self.image = None
        self.image_label = ttk.Label(self)
        self.image_label.pack(fill=tk.BOTH, expand=True)

        controls = ttk.Frame(self)
        controls.pack(fill=tk.X)

        self.csv_path_var = tk.StringVar()
        self.backend_var = tk.StringVar(value="local")
        ttk.Label(controls, text="CSV destino:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(controls, textvariable=self.csv_path_var, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="Elegir CSV", command=self.choose_csv).pack(side=tk.LEFT, padx=5)

        ttk.Button(controls, text="Pegar desde portapapeles", command=self.grab_clipboard).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="Abrir imagen...", command=self.open_image).pack(side=tk.LEFT, padx=5)
        # OCR backend
        ttk.Label(controls, text="Backend OCR:").pack(side=tk.LEFT, padx=5)
        ttk.OptionMenu(controls, self.backend_var, "local", "local", "azure").pack(side=tk.LEFT, padx=5)

        # Preprocessing options
        self.invert_var = tk.BooleanVar(value=True)
        self.threshold_var = tk.IntVar(value=160)
        ttk.Checkbutton(controls, text="Invertir (modo oscuro)", variable=self.invert_var).pack(side=tk.LEFT, padx=5)
        ttk.Label(controls, text="Umbral").pack(side=tk.LEFT, padx=2)
        self.threshold_spin = ttk.Spinbox(controls, from_=80, to=220, textvariable=self.threshold_var, width=5)
        self.threshold_spin.pack(side=tk.LEFT, padx=2)

        ttk.Button(controls, text="OCR", command=self.run_ocr).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="Guardar + Ajustar", command=self.save_and_fit).pack(side=tk.LEFT, padx=5)

        self.output = tk.Text(self, height=10)
        self.output.pack(fill=tk.X)

        self.check_tesseract()

    def check_tesseract(self):
        # Check selected backend
        if self.backend_var.get() == "local":
            if pytesseract is None:
                self.log("pytesseract no instalado. Instala Tesseract OCR y pytesseract.")
                return
            # Verify tesseract.exe on PATH
            path_exe = shutil.which("tesseract")
            if path_exe:
                self.log(f"Tesseract encontrado: {path_exe}")
            else:
                self.log("Tesseract NO está en PATH. Selecciona tesseract.exe...")
                exe = filedialog.askopenfilename(title="Selecciona tesseract.exe", filetypes=[("Exe", "*.exe")])
                if exe:
                    pytesseract.pytesseract.tesseract_cmd = exe
                    self.log(f"Usando tesseract en: {exe}")
                else:
                    self.log("No se configuró Tesseract; OCR local fallará.")
        else:
            # For Azure, just log env status
            import os
            ep = os.environ.get("AZURE_CV_ENDPOINT")
            k = os.environ.get("AZURE_CV_KEY")
            if ep and k:
                self.log("Azure OCR configurado por variables de entorno.")
            else:
                self.log("Azure OCR requiere AZURE_CV_ENDPOINT y AZURE_CV_KEY en entorno.")

    def choose_csv(self):
        path = filedialog.asksaveasfilename(title="CSV destino", defaultextension=".csv", filetypes=[("CSV", ".csv")])
        if path:
            self.csv_path_var.set(path)

    def grab_clipboard(self):
        # Grab image from clipboard
        clip = ImageGrab.grabclipboard()
        if isinstance(clip, Image.Image):
            self.image = clip
            self.show_image(clip)
            self.log("Imagen pegada desde portapapeles.")
            return
        # Sometimes Windows clipboard returns a list of file paths
        if isinstance(clip, list) and clip:
            path = clip[0]
            try:
                img = Image.open(path)
                self.image = img
                self.show_image(img)
                self.log(f"Imagen cargada desde archivo del portapapeles: {path}")
                return
            except Exception as e:
                self.log(f"No se pudo abrir la imagen del portapapeles: {e}")
                return
        self.log("No hay imagen en el portapapeles.")

    def open_image(self):
        path = filedialog.askopenfilename(title="Abrir imagen", filetypes=[
            ("Imágenes", "*.png;*.jpg;*.jpeg;*.bmp;*.webp"),
            ("PNG", "*.png"), ("JPEG", "*.jpg;*.jpeg"), ("BMP", "*.bmp"), ("WEBP", "*.webp"),
        ])
        if not path:
            return
        try:
            img = Image.open(path)
            self.image = img
            self.show_image(img)
            self.log(f"Imagen abierta: {path}")
        except Exception as e:
            self.log(f"Error abriendo la imagen: {e}")

    def show_image(self, img: Image.Image):
        # Resize to fit label
        w = self.image_label.winfo_width() or 700
        h = self.image_label.winfo_height() or 400
        img2 = img.copy()
        img2.thumbnail((w, h))
        self.tk_img = ImageTk.PhotoImage(img2)
        self.image_label.configure(image=self.tk_img)

    def run_ocr(self):
        if self.image is None:
            self.log("Primero pega una imagen.")
            return
        # Save to in-memory buffer and run OCR (with segmentation per line)
        buf = io.BytesIO()
        self.image.save(buf, format="PNG")
        buf.seek(0)
        # Write temp if needed
        tmp_path = os.path.join(os.getcwd(), "_tmp_ocr.png")
        with open(tmp_path, "wb") as f:
            f.write(buf.read())
        try:
            vals = extract_multipliers_from_image(
                tmp_path,
                invert=self.invert_var.get(),
                threshold=self.threshold_var.get(),
                backend=self.backend_var.get()
            )
            if vals:
                self.log(f"OCR detectó {len(vals)} valores: {vals[:10]}...")
                self.last_vals = vals
            else:
                self.log("OCR no detectó valores con formato 'N.NNx'.")
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    def save_and_fit(self):
        vals = getattr(self, 'last_vals', None)
        if not vals:
            self.log("No hay valores OCR para guardar.")
            return
        csv_path = self.csv_path_var.get().strip()
        if csv_path:
            append_to_csv(csv_path, vals, session_id="OCR")
            self.log(f"Guardado en {csv_path}.")
        # Fit models to the OCR values
        import numpy as np
        arr = np.array(vals)
        S = empirical_survival(arr)
        fits = fit_models(arr)
        best = best_model_by_aic(fits)
        self.log(summarize_fit(fits, best))

    def log(self, msg: str):
        self.output.insert(tk.END, msg + "\n")
        self.output.see(tk.END)


def main():
    app = OCRGui()
    app.mainloop()


if __name__ == "__main__":
    main()
