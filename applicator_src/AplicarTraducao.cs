using System;
using System.Drawing;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Windows.Forms;

namespace YsXPTBRApplicator
{
    internal static class Program
    {
        [STAThread]
        private static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new ApplyForm());
        }
    }

    internal sealed class ApplyForm : Form
    {
        private readonly TextBox gamePath = new TextBox();
        private readonly Label status = new Label();
        private readonly Button apply = new Button();

        public ApplyForm()
        {
            Text = "Aplicar Tradução PT-BR · Ys X Proud Nordics";
            ClientSize = new Size(720, 310);
            MinimumSize = new Size(660, 340);
            StartPosition = FormStartPosition.CenterScreen;
            BackColor = Color.FromArgb(22, 24, 33);
            ForeColor = Color.FromArgb(235, 237, 244);
            Font = new Font("Segoe UI", 10F);

            Controls.Add(MakeLabel("YS X · APLICADOR DA TRADUÇÃO PT-BR", 24, 20, 660, 26, true));
            Controls.Add(MakeLabel(
                "Selecione a pasta que contém ysx_pn.exe. O aplicador cria backup do mod anterior e não altera os arquivos originais do jogo.",
                24, 55, 660, 46, false));

            Controls.Add(MakeLabel("Pasta do jogo", 24, 112, 180, 24, false));
            gamePath.SetBounds(24, 138, 565, 31);
            gamePath.BackColor = Color.FromArgb(35, 38, 50);
            gamePath.ForeColor = Color.White;
            gamePath.BorderStyle = BorderStyle.FixedSingle;
            Controls.Add(gamePath);

            var browse = new Button { Text = "Procurar…" };
            browse.SetBounds(599, 136, 96, 35);
            StyleButton(browse, false);
            browse.Click += Browse;
            Controls.Add(browse);

            apply.Text = "Aplicar tradução";
            apply.SetBounds(24, 190, 180, 42);
            StyleButton(apply, true);
            apply.Click += ApplyTranslation;
            Controls.Add(apply);

            status.SetBounds(220, 188, 475, 75);
            status.ForeColor = Color.FromArgb(176, 184, 205);
            status.Text = FindTranslationFile() == null
                ? "Arquivo Traducao\\zzz_ysx_ptbr.p3a não encontrado."
                : "Pacote de tradução localizado e pronto para aplicar.";
            Controls.Add(status);

            Controls.Add(MakeLabel("Aplicador 1.0.0 · instalação reversível · log SHA-256", 24, 274, 650, 22, false));
        }

        private static Label MakeLabel(string text, int x, int y, int width, int height, bool title)
        {
            return new Label {
                Text = text, Left = x, Top = y, Width = width, Height = height,
                Font = new Font("Segoe UI", title ? 12F : 9.5F, title ? FontStyle.Bold : FontStyle.Regular)
            };
        }

        private static void StyleButton(Button button, bool primary)
        {
            button.FlatStyle = FlatStyle.Flat;
            button.FlatAppearance.BorderSize = 1;
            button.FlatAppearance.BorderColor = primary ? Color.FromArgb(139, 108, 218) : Color.FromArgb(85, 90, 108);
            button.BackColor = primary ? Color.FromArgb(111, 78, 190) : Color.FromArgb(35, 38, 50);
            button.ForeColor = Color.White;
        }

        private void Browse(object sender, EventArgs e)
        {
            using (var dialog = new FolderBrowserDialog())
            {
                dialog.Description = "Selecione a pasta de Ys X Proud Nordics";
                if (dialog.ShowDialog(this) == DialogResult.OK)
                    gamePath.Text = dialog.SelectedPath;
            }
        }

        private static string FindTranslationFile()
        {
            string root = AppDomain.CurrentDomain.BaseDirectory;
            string[] candidates = {
                Path.GetFullPath(Path.Combine(root, "..", "Traducao", "zzz_ysx_ptbr.p3a")),
                Path.Combine(root, "zzz_ysx_ptbr.p3a")
            };
            foreach (string candidate in candidates)
                if (File.Exists(candidate)) return candidate;
            return null;
        }

        private void ApplyTranslation(object sender, EventArgs e)
        {
            string game = gamePath.Text.Trim();
            string package = FindTranslationFile();
            if (package == null)
            {
                Fail("O arquivo Traducao\\zzz_ysx_ptbr.p3a não foi encontrado.");
                return;
            }
            if (!File.Exists(Path.Combine(game, "ysx_pn.exe")) || !File.Exists(Path.Combine(game, "script.p3a")))
            {
                Fail("A pasta selecionada não parece ser uma instalação válida de Ys X Proud Nordics.");
                return;
            }

            apply.Enabled = false;
            try
            {
                string mods = Path.Combine(game, "mods");
                Directory.CreateDirectory(mods);
                string destination = Path.Combine(mods, "zzz_ysx_ptbr.p3a");
                string temporary = destination + ".tmp";
                string backup = "";

                if (File.Exists(destination))
                {
                    string backupDir = Path.Combine(mods, "backup_ptbr", DateTime.Now.ToString("yyyyMMdd_HHmmss"));
                    Directory.CreateDirectory(backupDir);
                    backup = Path.Combine(backupDir, Path.GetFileName(destination));
                    File.Copy(destination, backup, false);
                }

                File.Copy(package, temporary, true);
                string sourceHash = Sha256(package);
                string temporaryHash = Sha256(temporary);
                if (!String.Equals(sourceHash, temporaryHash, StringComparison.OrdinalIgnoreCase))
                    throw new IOException("A cópia temporária não corresponde ao pacote de tradução.");

                if (File.Exists(destination)) File.Replace(temporary, destination, null);
                else File.Move(temporary, destination);

                string installedHash = Sha256(destination);
                if (!String.Equals(sourceHash, installedHash, StringComparison.OrdinalIgnoreCase))
                    throw new IOException("O arquivo instalado falhou na conferência SHA-256.");

                WriteLog("SUCESSO", package, destination, sourceHash, backup, "");
                status.ForeColor = Color.FromArgb(139, 204, 172);
                status.Text = "Tradução aplicada com sucesso.\n" + destination;
                MessageBox.Show(this, "Tradução aplicada com sucesso.\n\n" + destination +
                    (backup.Length > 0 ? "\n\nBackup: " + backup : ""), "Concluído",
                    MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            catch (Exception ex)
            {
                WriteLog("ERRO", package, game, "", "", ex.ToString());
                Fail("Não foi possível aplicar a tradução:\n" + ex.Message);
            }
            finally { apply.Enabled = true; }
        }

        private void Fail(string message)
        {
            status.ForeColor = Color.FromArgb(229, 151, 151);
            status.Text = message;
            MessageBox.Show(this, message, "Aplicador PT-BR", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }

        private static string Sha256(string path)
        {
            using (var sha = SHA256.Create())
            using (var stream = File.OpenRead(path))
            {
                byte[] hash = sha.ComputeHash(stream);
                var text = new StringBuilder(hash.Length * 2);
                foreach (byte value in hash) text.Append(value.ToString("x2"));
                return text.ToString();
            }
        }

        private static void WriteLog(string result, string source, string destination,
                                     string hash, string backup, string detail)
        {
            string log = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Aplicador_YsX.log");
            string entry = String.Join(Environment.NewLine, new[] {
                "[" + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "] " + result,
                "Fonte: " + source,
                "Destino: " + destination,
                "SHA-256: " + hash,
                "Backup: " + (backup.Length > 0 ? backup : "não necessário"),
                detail.Length > 0 ? "Detalhe: " + detail : "",
                new String('-', 72), ""
            });
            File.AppendAllText(log, entry, new UTF8Encoding(true));
        }
    }
}
