using System;
using System.IO;
using System.Text;
using System.Drawing;
using System.Diagnostics;
using System.Security.Cryptography;
using System.Reflection;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using System.Collections.Generic;

namespace YsXShare {
public class Manifest { public string version; public string exe_sha256; public string script_sha256; public string patch_sha256; }
public class State { public string installed; public string previous; public string backup; }
public static class Engine {
 public static string Hash(string path) { using(var h=SHA256.Create()) using(var s=File.OpenRead(path)) return BitConverter.ToString(h.ComputeHash(s)).Replace("-", "").ToLowerInvariant(); }
 public static T Read<T>(string path) { return new JavaScriptSerializer().Deserialize<T>(File.ReadAllText(path)); }
 public static void Write(string path, object data) { File.WriteAllText(path, new JavaScriptSerializer().Serialize(data), new UTF8Encoding(false)); }
 public static string StatePath(string game) { return Path.Combine(game,"mods","ysx_ptbr_instalacao.json"); }
 public static string Target(string game) { return Path.Combine(game,"mods","zzz_ysx_ptbr.p3a"); }
 public static void Validate(string game, Manifest m) {
  if(!File.Exists(Path.Combine(game,"ysx_pn.exe")) || !File.Exists(Path.Combine(game,"script.p3a"))) throw new IOException("Selecione a pasta que contém ysx_pn.exe e script.p3a.");
  foreach(var p in Process.GetProcessesByName("ysx_pn")) { p.Dispose(); throw new IOException("Feche o jogo antes de aplicar ou restaurar."); }
  if(Hash(Path.Combine(game,"ysx_pn.exe"))!=m.exe_sha256 || Hash(Path.Combine(game,"script.p3a"))!=m.script_sha256) throw new IOException("Versão incompatível. Este pacote foi verificado para "+m.version+". Nenhum arquivo foi alterado.");
 }
 public static string Backup(string game, string source) {
  var folder=Path.Combine(game,"mods","backup_ptbr",DateTime.Now.ToString("yyyyMMdd_HHmmss_fff")+"_"+Guid.NewGuid().ToString("N")); Directory.CreateDirectory(folder);
  var dest=Path.Combine(folder,Path.GetFileName(source)); File.Copy(source,dest,false);
  if(Hash(dest)!=Hash(source)) throw new IOException("Falha na conferência do backup."); return dest;
 }
 static void Replace(string source,string target) { if(File.Exists(target)) File.Replace(source,target,null); else File.Move(source,target); }
 static void Recover(string game) {
  var pending=StatePath(game)+".pending";
  if(!File.Exists(pending)) return;
  var state=Read<State>(pending);
  if(File.Exists(Target(game)) && Hash(Target(game))==state.installed) Replace(pending,StatePath(game));
  else throw new IOException("Há uma instalação interrompida. Nenhum arquivo será sobrescrito. Preserve o arquivo .pending e o backup para recuperação.");
 }
 public static void Apply(string game, string patch, Manifest m) {
  if(Hash(patch)!=m.patch_sha256) throw new IOException("Pacote corrompido: SHA-256 não confere.");
  Recover(game);
  Directory.CreateDirectory(Path.Combine(game,"mods")); var target=Target(game); var sp=StatePath(game);
  State state;
  if(File.Exists(sp)) { state=Read<State>(sp); if(!File.Exists(target)||Hash(target)!=state.installed) throw new IOException("O mod mudou desde a instalação. Restaure/resolva essa alteração antes de atualizar."); }
  else { state=new State(); state.previous=File.Exists(target)?Hash(target):""; state.backup=""; }
  if(File.Exists(target)) { var b=Backup(game,target); if(state.backup=="" && state.previous!="") state.backup=b; }
  var tmp=target+"."+Guid.NewGuid().ToString("N")+".novo"; var pending=sp+".pending";
  try {
   File.Copy(patch,tmp,false); if(Hash(tmp)!=m.patch_sha256) throw new IOException("Cópia inválida.");
   // Persist recovery information before replacing the mod.
   state.installed=m.patch_sha256; Write(pending,state); Replace(tmp,target); Replace(pending,sp);
   File.AppendAllText(Path.Combine(game,"mods","ysx_ptbr.log"),DateTime.Now.ToString("s")+" APLICADO "+state.installed+" backup="+state.backup+Environment.NewLine);
  } finally { if(File.Exists(tmp)) File.Delete(tmp); }
 }
 public static void Restore(string game) {
  Recover(game);
  var sp=StatePath(game); if(!File.Exists(sp)) throw new IOException("Não há instalação registrada por este instalador. Para ZIP manual, siga o guia de restauração.");
  var state=Read<State>(sp); var target=Target(game);
  if(!File.Exists(target)||Hash(target)!=state.installed) throw new IOException("O mod foi alterado depois da instalação. Restauração bloqueada para preservar suas alterações.");
  string previous=null;
  if(state.previous!="") {
   var root=Path.GetFullPath(Path.Combine(game,"mods","backup_ptbr"))+Path.DirectorySeparatorChar;
   previous=Path.GetFullPath(state.backup);
   if(!previous.StartsWith(root,StringComparison.OrdinalIgnoreCase)||!File.Exists(previous)||Hash(previous)!=state.previous) throw new IOException("Backup anterior ausente, inválido ou fora da pasta autorizada.");
  }
  var saved=Backup(game,target);
  if(previous!=null) { var tmp=target+".restaurar"; File.Copy(previous,tmp,false); if(Hash(tmp)!=state.previous) throw new IOException("Backup inválido."); Replace(tmp,target); }
  else File.Move(target,Path.Combine(Path.GetDirectoryName(saved),"traducao_removida.p3a"));
  File.Move(sp,Path.Combine(Path.GetDirectoryName(saved),"instalacao_restaurada.json"));
  File.AppendAllText(Path.Combine(game,"mods","ysx_ptbr.log"),DateTime.Now.ToString("s")+" RESTAURADO backup="+saved+Environment.NewLine);
 }
}
public class Installer:Form {
 TextBox folder=new TextBox(); Label status=new Label(); Manifest manifest;
 public Installer() {
  Text="Ys X · Instalador PT-BR com restauração"; ClientSize=new Size(730,330); Font=new Font("Segoe UI",10); StartPosition=FormStartPosition.CenterScreen;
  var title=new Label {Text="INSTALAR OU DESFAZER A TRADUÇÃO",Left=24,Top=20,Width=680,Height=30}; Controls.Add(title);
  Controls.Add(new Label {Text="Selecione a pasta do jogo. A versão será conferida e o mod anterior preservado.\nFeche o jogo antes de continuar. Os arquivos originais não são substituídos.",Left=24,Top=60,Width=680,Height=65});
  folder.SetBounds(24,135,550,30); Controls.Add(folder);
  var browse=new Button {Text="Procurar…",Left=585,Top=133,Width=120,Height=34}; browse.Click+=(s,e)=>{using(var d=new FolderBrowserDialog()) if(d.ShowDialog()==DialogResult.OK) folder.Text=d.SelectedPath;}; Controls.Add(browse);
  var apply=new Button {Text="Aplicar tradução",Left=24,Top=185,Width=190,Height=42};
  var restore=new Button {Text="Restaurar / desfazer",Left=230,Top=185,Width=210,Height=42}; Controls.Add(apply); Controls.Add(restore);
  status.SetBounds(24,245,680,65); Controls.Add(status);
  using(var stream=Assembly.GetExecutingAssembly().GetManifestResourceStream("manifest.json")) using(var reader=new StreamReader(stream)) manifest=new JavaScriptSerializer().Deserialize<Manifest>(reader.ReadToEnd());
  status.Text="Versão compatível: "+manifest.version+" · pacote incorporado · SHA-256";
  apply.Click+=(s,e)=>Run(false); restore.Click+=(s,e)=>Run(true);
 }
 void Run(bool restore) {
  string temp=null;
  try {
   var game=Path.GetFullPath(folder.Text.Trim()); Engine.Validate(game,manifest);
   if(MessageBox.Show(this,restore?"Restaurar o estado anterior? A tradução atual será preservada em backup.":"Aplicar a tradução com backup?","Confirmar",MessageBoxButtons.YesNo)!=DialogResult.Yes) return;
   if(restore) Engine.Restore(game); else {
    temp=Path.GetTempFileName(); using(var input=Assembly.GetExecutingAssembly().GetManifestResourceStream("patch.p3a")) using(var output=File.Create(temp)) input.CopyTo(output);
    Engine.Apply(game,temp,manifest);
   }
   status.Text=restore?"Estado anterior restaurado. Backups preservados.":"Tradução aplicada. Reabra o jogo com o idioma inglês.";
   MessageBox.Show(this,status.Text,"Concluído");
  } catch(Exception ex) { status.Text=ex.Message; MessageBox.Show(this,ex.Message,"Operação não concluída",MessageBoxButtons.OK,MessageBoxIcon.Error); }
  finally { if(temp!=null && File.Exists(temp)) File.Delete(temp); }
 }
 [STAThread] public static void Main() { Application.EnableVisualStyles(); Application.Run(new Installer()); }
}
}
