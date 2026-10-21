using System;
using System.IO;
using YsXShare;
public static class SharingEngineTests {
 static int count=0;
 static void Check(bool ok,string label) { if(!ok) throw new Exception(label); count++; }
 static void Reject(Action action,string label) { bool failed=false; try{action();}catch(IOException){failed=true;} Check(failed,label); }
 public static void Main(string[] args) {
  if(args.Length==2 && args[0]=="--verify-package") {
   var assembly=System.Reflection.Assembly.LoadFile(Path.GetFullPath(args[1]));
   Manifest manifest;
   using(var stream=assembly.GetManifestResourceStream("manifest.json")) using(var reader=new StreamReader(stream))
    manifest=new System.Web.Script.Serialization.JavaScriptSerializer().Deserialize<Manifest>(reader.ReadToEnd());
   using(var stream=assembly.GetManifestResourceStream("patch.p3a")) using(var sha=System.Security.Cryptography.SHA256.Create())
    Check(BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant()==manifest.patch_sha256,"embedded patch hash");
   Check(manifest.version=="Ys X Proud Nordics 1.0.3_r10","compatible version");
   Console.WriteLine(count+" embedded package checks passed (.NET Framework parser)"); return;
  }
  var root=Path.GetFullPath(args[0]); Directory.CreateDirectory(root);
  File.WriteAllText(Path.Combine(root,"ysx_pn.exe"),"game"); File.WriteAllText(Path.Combine(root,"script.p3a"),"script");
  var patch=Path.Combine(root,"patch.p3a"); File.WriteAllText(patch,"translation");
  var m=new Manifest {version="test",exe_sha256=Engine.Hash(Path.Combine(root,"ysx_pn.exe")),script_sha256=Engine.Hash(Path.Combine(root,"script.p3a")),patch_sha256=Engine.Hash(patch)};
  Engine.Validate(root,m); count++;
  m.exe_sha256="wrong"; Reject(()=>Engine.Validate(root,m),"wrong version"); m.exe_sha256=Engine.Hash(Path.Combine(root,"ysx_pn.exe"));
  m.patch_sha256="wrong"; Reject(()=>Engine.Apply(root,patch,m),"corrupt patch"); m.patch_sha256=Engine.Hash(patch);
  Engine.Apply(root,patch,m); Check(Engine.Hash(Engine.Target(root))==m.patch_sha256,"install without previous");
  File.Move(Engine.StatePath(root),Engine.StatePath(root)+".pending"); Engine.Apply(root,patch,m);
  Check(File.Exists(Engine.StatePath(root)) && !File.Exists(Engine.StatePath(root)+".pending"),"recover interrupted state promotion");
  Engine.Restore(root); Check(!File.Exists(Engine.Target(root)),"remove first install");
  File.WriteAllText(Engine.Target(root),"previous"); var previous=Engine.Hash(Engine.Target(root));
  Engine.Apply(root,patch,m); Engine.Apply(root,patch,m); Engine.Restore(root); Check(Engine.Hash(Engine.Target(root))==previous,"repeat apply restores original baseline");
  Engine.Apply(root,patch,m); File.WriteAllText(Engine.Target(root),"external modification"); Reject(()=>Engine.Restore(root),"protect external modification");
  File.Copy(patch,Engine.Target(root),true); var state=Engine.Read<State>(Engine.StatePath(root)); var originalBackup=state.backup;
  state.backup=patch; Engine.Write(Engine.StatePath(root),state); Reject(()=>Engine.Restore(root),"reject backup outside root");
  state.backup=originalBackup; Engine.Write(Engine.StatePath(root),state); File.WriteAllText(originalBackup,"corrupted backup"); Reject(()=>Engine.Restore(root),"corrupt backup");
  Check(File.ReadAllText(Engine.Target(root))=="translation","failed restoration leaves mod intact");
  Console.WriteLine(count+" installer engine checks passed");
 }
}
