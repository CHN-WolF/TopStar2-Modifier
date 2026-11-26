using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

internal class TopStar2Patcher
{
    private static readonly string[] ItemPropNames = new[]
    {
        "SingleShield", "AlmightyShield", "TimeShield",
        "SpeedDown1", "SpeedDown2", "SpeedDown3", "SpeedDown4",
        "SpeedUp1", "SpeedUp2", "SpeedUp3", "SpeedUp4",
        "ExperienceA", "ExperienceB", "ExperienceC", "ExperienceD",
        "MirrorX", "MirrorY", "MirrorXY"
    };

    private static readonly Dictionary<string, string> PcbEntryPoints = new Dictionary<string, string>
    {
        { "PCBLib_Init", "?PCBLib_Init@@YAFGK@Z" },
        { "PCBLib_Exit", "?PCBLib_Exit@@YAXXZ" },
        { "PCBLib_GetCoin1", "?PCBLib_GetCoin1@@YAKXZ" },
        { "PCBLib_SetCoin1Drive", "?PCBLib_SetCoin1Drive@@YAXG@Z" },
        { "PCBLib_SetCoin1Lockout", "?PCBLib_SetCoin1Lockout@@YAXG@Z" },
        { "PCBLib_SetCoin2Drive", "?PCBLib_SetCoin2Drive@@YAXG@Z" },
        { "PCBLib_SetCoin2Lockout", "?PCBLib_SetCoin2Lockout@@YAXG@Z" },
        { "PCBLib_SetCoinDriveTime", "?PCBLib_SetCoinDriveTime@@YAXGG@Z" },
        { "PCBLib_IsConnect", "?PCBLib_IsConnect@@YAGXZ" },
        { "PCBLib_GetErrorStatus", "?PCBLib_GetErrorStatus@@YAKXZ" },
        { "PCBLib_SetLEDControl", "?PCBLib_SetLEDControl@@YAXG@Z" },
        { "PCBLib_SetLEDOnNumber", "?PCBLib_SetLEDOnNumber@@YAXGG@Z" },
        { "PCBLib_SetLEDOnBit", "?PCBLib_SetLEDOnBit@@YAXG@Z" },
        { "PCBLib_SetLEDColor", "?PCBLib_SetLEDColor@@YAXGG@Z" },
        { "PCBLib_SetLEDColorDirect", "?PCBLib_SetLEDColorDirect@@YAXGGGG@Z" },
        { "PCBLib_SetLEDUserPattern", "?PCBLib_SetLEDUserPattern@@YAXGGGG@Z" },
        { "PCBLib_SetLEDUserPatternData", "?PCBLib_SetLEDUserPatternData@@YAXGGG@Z" },
        { "PCBLib_RefreshStatus", "?PCBLib_RefreshStatus@@YAGXZ" },
        { "PCBLib_Timer", "?PCBLib_Timer@@YAXXZ" },
        { "PCBLib_GetStatus1", "?PCBLib_GetStatus1@@YAKXZ" },
        { "PCBLib_GetStatus2", "?PCBLib_GetStatus2@@YAKXZ" },
        { "PCBLib_SetInMeterAutoCountUp", "?PCBLib_SetInMeterAutoCountUp@@YAXG@Z" },
        { "PCBLib_SetMotorAccelSteps", "?PCBLib_SetMotorAccelStep@@YAXGG@Z" },
        { "PCBLib_GetLibVersion", "?PCBLib_GetLibVersion@@YAJXZ" },
        { "PCBLib_GetPCBVersion", "?PCBLib_GetPCBVersion@@YAJXZ" },
    };

    private static int Main(string[] args)
    {
        if (args.Length < 2)
        {
            Console.Error.WriteLine("Usage: TopStar2Patcher.exe <inspect|apply> <Assembly-CSharp.dll> [choices.txt]");
            return 1;
        }
        string cmd = args[0].ToLowerInvariant();
        string dllPath = Path.GetFullPath(args[1]);
        if (!File.Exists(dllPath))
        {
            Console.Error.WriteLine("File not found: " + dllPath);
            return 1;
        }

        var resolver = new DefaultAssemblyResolver();
        resolver.AddSearchDirectory(Path.GetDirectoryName(dllPath));
        resolver.AddSearchDirectory(AppDomain.CurrentDomain.BaseDirectory);
        var readerParams = new ReaderParameters { AssemblyResolver = resolver };

        try
        {
            if (cmd == "inspect")
            {
                using (var ad = AssemblyDefinition.ReadAssembly(dllPath, readerParams))
                {
                    InspectAll(ad.MainModule);
                }
                return 0;
            }
            if (cmd == "apply")
            {
                if (args.Length < 3 || !File.Exists(args[2]))
                {
                    Console.Error.WriteLine("Missing choices file.");
                    return 1;
                }
                var choices = ParseChoices(args[2]);
                string tmpPath = dllPath + ".tmp";
                bool changed;
                using (var ad = AssemblyDefinition.ReadAssembly(dllPath, readerParams))
                {
                    changed = ApplyAll(ad.MainModule, resolver, choices);
                    if (changed)
                    {
                        ad.Write(tmpPath);
                    }
                }
                if (changed)
                {
                    File.Delete(dllPath);
                    File.Move(tmpPath, dllPath);
                }
                return 0;
            }
            Console.Error.WriteLine("Unknown command: " + cmd);
            return 1;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex.Message);
            return 1;
        }
    }

    private static Dictionary<string, string> ParseChoices(string path)
    {
        var dict = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var raw in File.ReadAllLines(path))
        {
            var line = raw.Trim();
            if (string.IsNullOrEmpty(line)) continue;
            int eq = line.IndexOf('=');
            if (eq <= 0) continue;
            dict[line.Substring(0, eq).Trim()] = line.Substring(eq + 1).Trim();
        }
        return dict;
    }

    private static TypeDefinition FindType(ModuleDefinition mod, string fullName)
    {
        return mod.Types.FirstOrDefault(t => t.FullName == fullName);
    }

    private static MethodDefinition FindMethod(TypeDefinition type, string name)
    {
        return type == null ? null : type.Methods.FirstOrDefault(m => m.Name == name);
    }

    // --- Hold timers ---
    private static int FindHoldIndex(MethodDefinition m, string fieldName)
    {
        if (m == null || !m.HasBody) return -1;
        var il = m.Body.Instructions;
        for (int i = 0; i <= il.Count - 6; i++)
        {
            // Original: ldarg.0; dup; ldfld <field>; call get_deltaTime; sub; stfld <field>
            if (il[i].OpCode == OpCodes.Ldarg_0 &&
                il[i + 1].OpCode == OpCodes.Dup &&
                il[i + 2].OpCode == OpCodes.Ldfld &&
                ((FieldReference)il[i + 2].Operand).Name == fieldName &&
                il[i + 3].OpCode == OpCodes.Call &&
                il[i + 3].Operand.ToString().Contains("get_deltaTime") &&
                il[i + 4].OpCode == OpCodes.Sub &&
                il[i + 5].OpCode == OpCodes.Stfld &&
                ((FieldReference)il[i + 5].Operand).Name == fieldName)
            {
                return i;
            }
            // Patched: ldarg.0; ldc.r4 <sec>; stfld <field>; nop; nop; nop (or without nops)
            if (il[i].OpCode == OpCodes.Ldarg_0 &&
                il[i + 1].OpCode == OpCodes.Ldc_R4 &&
                il[i + 2].OpCode == OpCodes.Stfld &&
                ((FieldReference)il[i + 2].Operand).Name == fieldName)
            {
                return i;
            }
        }
        return -1;
    }

    private static string InspectHold(ModuleDefinition mod, string typeName, string fieldName, int defSec)
    {
        var m = FindMethod(FindType(mod, typeName), "Update");
        int idx = FindHoldIndex(m, fieldName);
        if (idx < 0) return "unknown";
        var il = m.Body.Instructions;
        if (il[idx + 1].OpCode == OpCodes.Dup) return "open|" + defSec;
        if (il[idx + 1].OpCode == OpCodes.Ldc_R4)
        {
            float sec = (float)il[idx + 1].Operand;
            return "locked|" + sec.ToString("G", System.Globalization.CultureInfo.InvariantCulture);
        }
        return "unknown";
    }

    private static bool ApplyHold(ModuleDefinition mod, string key, string typeName, string fieldName, bool lockIt, float seconds, List<string> notes)
    {
        var t = FindType(mod, typeName);
        var m = FindMethod(t, "Update");
        int idx = FindHoldIndex(m, fieldName);
        if (idx < 0) throw new Exception("Hold pattern not found for " + key);
        var il = m.Body.Instructions;
        bool isLocked = il[idx + 1].OpCode == OpCodes.Ldc_R4;
        if (lockIt)
        {
            if (isLocked && Math.Abs((float)il[idx + 1].Operand - seconds) < 1e-4f) return false;
            var fieldRef = t.Fields.First(f => f.Name == fieldName);
            if (!isLocked)
            {
                // Replace 6 instructions in-place: ldarg.0, ldc.r4, stfld, nop, nop, nop
                il[idx + 1].OpCode = OpCodes.Ldc_R4;
                il[idx + 1].Operand = seconds;
                il[idx + 2].OpCode = OpCodes.Stfld;
                il[idx + 2].Operand = fieldRef;
                il[idx + 3].OpCode = OpCodes.Nop;
                il[idx + 3].Operand = null;
                il[idx + 4].OpCode = OpCodes.Nop;
                il[idx + 4].Operand = null;
                il[idx + 5].OpCode = OpCodes.Nop;
                il[idx + 5].Operand = null;
            }
            else
            {
                il[idx + 1].Operand = seconds;
            }
            notes.Add("NOTE:" + key + ":locked:" + seconds.ToString("G", System.Globalization.CultureInfo.InvariantCulture));
            return true;
        }
        else
        {
            if (!isLocked) return false;
            var fieldRef = t.Fields.First(f => f.Name == fieldName);
            MethodReference getDelta = null;
            foreach (var r in mod.AssemblyReferences)
            {
                if (r.Name == "UnityEngine")
                {
                    var ue = mod.AssemblyResolver.Resolve(r);
                    var tt = ue.MainModule.Types.First(x => x.FullName == "UnityEngine.Time");
                    getDelta = mod.ImportReference(tt.Methods.First(x => x.Name == "get_deltaTime"));
                    break;
                }
            }
            if (getDelta == null) throw new Exception("UnityEngine.Time.get_deltaTime not found");
            // Need 6 slots starting at idx
            var p = m.Body.GetILProcessor();
            while (il.Count <= idx + 5 || (il[idx + 3].OpCode != OpCodes.Nop))
            {
                p.InsertAfter(il[idx + 2], p.Create(OpCodes.Nop));
                if (il.Count > idx + 5 && il[idx + 3].OpCode == OpCodes.Nop && il[idx + 4].OpCode == OpCodes.Nop && il[idx + 5].OpCode == OpCodes.Nop)
                    break;
            }
            il[idx + 1].OpCode = OpCodes.Dup; il[idx + 1].Operand = null;
            il[idx + 2].OpCode = OpCodes.Ldfld; il[idx + 2].Operand = fieldRef;
            il[idx + 3].OpCode = OpCodes.Call; il[idx + 3].Operand = getDelta;
            il[idx + 4].OpCode = OpCodes.Sub; il[idx + 4].Operand = null;
            il[idx + 5].OpCode = OpCodes.Stfld; il[idx + 5].Operand = fieldRef;
            notes.Add("NOTE:" + key + ":open");
            return true;
        }
    }

    // --- Play timer (TimeLimitManage.get_RemainTimeMs) ---
    private static string InspectPlay(ModuleDefinition mod)
    {
        var m = FindMethod(FindType(mod, "TimeLimitManage"), "get_RemainTimeMs");
        if (m == null || !m.HasBody) return "unknown";
        var il = m.Body.Instructions;
        if (il.Count >= 2 && il[0].OpCode == OpCodes.Ldc_I4 && il[1].OpCode == OpCodes.Ret)
        {
            int ms = (int)il[0].Operand;
            if (ms > 0 && ms % 1000 == 0) return "locked|" + (ms / 1000);
        }
        if (il.Any(i => i.OpCode == OpCodes.Ldc_I4 && (int)i.Operand == 99000)) return "open|90";
        return "unknown";
    }

    private static bool ApplyPlay(ModuleDefinition mod, bool lockIt, int seconds, List<string> notes)
    {
        var m = FindMethod(FindType(mod, "TimeLimitManage"), "get_RemainTimeMs");
        if (m == null || !m.HasBody) throw new Exception("TimeLimitManage.get_RemainTimeMs not found");
        var il = m.Body.Instructions;
        bool isLocked = il.Count >= 2 && il[0].OpCode == OpCodes.Ldc_I4 && il[1].OpCode == OpCodes.Ret;
        int ms = seconds * 1000;
        if (lockIt)
        {
            if (isLocked && (int)il[0].Operand == ms) return false;
            if (isLocked)
            {
                il[0].Operand = ms;
            }
            else
            {
                var p = m.Body.GetILProcessor();
                var first = il[0];
                p.InsertBefore(first, p.Create(OpCodes.Ldc_I4, ms));
                p.InsertBefore(first, p.Create(OpCodes.Ret));
            }
            notes.Add("NOTE:play:locked:" + seconds);
            return true;
        }
        else
        {
            if (!isLocked) return false;
            var p = m.Body.GetILProcessor();
            p.Remove(il[0]);
            p.Remove(il[0]);
            notes.Add("NOTE:play:open");
            return true;
        }
    }

    // --- Tutorial ---
    private static List<Instruction> FindTutorialLdstrs(ModuleDefinition mod)
    {
        var list = new List<Instruction>();
        var targets = new[]
        {
            new { Type = "ModeSelect", Nested = "SwitchToJourneyMode" },
            new { Type = "ModeSelect", Nested = "SwitchToMatchMode" },
            new { Type = "PlayBeforeReminderSwitchScene", Nested = "<Start>" },
            new { Type = "PlayerSignIn", Nested = "ToGuestMode" },
        };
        foreach (var tgt in targets)
        {
            var t = FindType(mod, tgt.Type);
            if (t == null) continue;
            var nt = t.NestedTypes.FirstOrDefault(x => x.Name.Contains(tgt.Nested));
            var m = FindMethod(nt, "MoveNext");
            if (m == null || !m.HasBody) continue;
            var il = m.Body.Instructions;
            for (int i = 0; i < il.Count - 1; i++)
            {
                if (il[i].OpCode == OpCodes.Ldstr &&
                    (il[i + 1].OpCode == OpCodes.Callvirt || il[i + 1].OpCode == OpCodes.Call) &&
                    il[i + 1].Operand.ToString().Contains("SceneManager::LoadLevel"))
                {
                    var s = (string)il[i].Operand;
                    if (s == "Sign_In") continue;
                    if (s == "Tutorial" || s == "Song_Select" || s == "Title")
                    {
                        list.Add(il[i]);
                        break;
                    }
                }
            }
        }
        return list;
    }

    private static string InspectTutorial(ModuleDefinition mod)
    {
        var sites = FindTutorialLdstrs(mod);
        if (sites.Count != 4) return "unknown";
        if (sites.All(i => (string)i.Operand == "Tutorial")) return "open";
        if (sites.All(i => (string)i.Operand == "Song_Select")) return "locked";
        return "unknown";
    }

    private static bool ApplyTutorial(ModuleDefinition mod, bool lockIt, List<string> notes)
    {
        var sites = FindTutorialLdstrs(mod);
        if (sites.Count != 4) throw new Exception("Tutorial sites mismatch: found " + sites.Count);
        string target = lockIt ? "Song_Select" : "Tutorial";
        if (sites.All(i => (string)i.Operand == target)) return false;
        foreach (var i in sites) i.Operand = target;
        notes.Add("NOTE:tutorial:" + (lockIt ? "locked" : "open"));
        return true;
    }

    // --- LockMusicControl.CheckLockType (clear & offline) ---
    private static bool FindLockSites(ModuleDefinition mod, out Instruction offlineIns, out Instruction advIns, out Instruction masterIns)
    {
        offlineIns = advIns = masterIns = null;
        var m = FindMethod(FindType(mod, "LockMusicControl"), "CheckLockType");
        if (m == null || !m.HasBody) return false;
        var il = m.Body.Instructions;

        // 1. Offline: after get_Online() -> brtrue -> ldc.i4.{0|1}; ret
        for (int i = 0; i < il.Count - 3; i++)
        {
            if (il[i].OpCode == OpCodes.Call && il[i].Operand.ToString().Contains("get_Online") &&
                (il[i + 1].OpCode == OpCodes.Brtrue || il[i + 1].OpCode == OpCodes.Brtrue_S) &&
                (il[i + 2].OpCode == OpCodes.Ldc_I4_1 || il[i + 2].OpCode == OpCodes.Ldc_I4_0) &&
                il[i + 3].OpCode == OpCodes.Ret)
            {
                offlineIns = il[i + 2];
                break;
            }
        }
        // 2. Advanced: MusicUnlocked -> brtrue -> ldarg.1; ldc.i4.1; bne.un(.s); ldc.i4.{0|2}; ret
        for (int i = 2; i < il.Count - 3; i++)
        {
            if (il[i - 2].OpCode == OpCodes.Brtrue || il[i - 2].OpCode == OpCodes.Brtrue_S)
            {
                if (il[i - 1].OpCode == OpCodes.Ldarg_1 &&
                    il[i].OpCode == OpCodes.Ldc_I4_1 &&
                    (il[i + 1].OpCode == OpCodes.Bne_Un || il[i + 1].OpCode == OpCodes.Bne_Un_S) &&
                    (il[i + 2].OpCode == OpCodes.Ldc_I4_2 || il[i + 2].OpCode == OpCodes.Ldc_I4_0) &&
                    il[i + 3].OpCode == OpCodes.Ret)
                {
                    advIns = il[i + 2];
                }
            }
        }
        // 3. Master: MusicUnlocked -> brtrue -> ldarg.1; ldc.i4.2; bne.un(.s); ldc.i4.{0|3}; ret
        for (int i = 2; i < il.Count - 3; i++)
        {
            if (il[i - 2].OpCode == OpCodes.Brtrue || il[i - 2].OpCode == OpCodes.Brtrue_S)
            {
                if (il[i - 1].OpCode == OpCodes.Ldarg_1 &&
                    il[i].OpCode == OpCodes.Ldc_I4_2 &&
                    (il[i + 1].OpCode == OpCodes.Bne_Un || il[i + 1].OpCode == OpCodes.Bne_Un_S) &&
                    (il[i + 2].OpCode == OpCodes.Ldc_I4_3 || il[i + 2].OpCode == OpCodes.Ldc_I4_0) &&
                    il[i + 3].OpCode == OpCodes.Ret)
                {
                    masterIns = il[i + 2];
                }
            }
        }
        return offlineIns != null && advIns != null && masterIns != null;
    }

    private static string InspectOffline(ModuleDefinition mod)
    {
        Instruction o, a, m;
        if (!FindLockSites(mod, out o, out a, out m)) return "unknown";
        if (o.OpCode == OpCodes.Ldc_I4_1) return "open";
        if (o.OpCode == OpCodes.Ldc_I4_0) return "locked";
        return "unknown";
    }

    private static string InspectClear(ModuleDefinition mod)
    {
        Instruction o, a, m;
        if (!FindLockSites(mod, out o, out a, out m)) return "unknown";
        if (a.OpCode == OpCodes.Ldc_I4_2 && m.OpCode == OpCodes.Ldc_I4_3) return "open";
        if (a.OpCode == OpCodes.Ldc_I4_0 && m.OpCode == OpCodes.Ldc_I4_0) return "locked";
        return "unknown";
    }

    private static bool ApplyOffline(ModuleDefinition mod, bool lockIt, List<string> notes)
    {
        Instruction o, a, m;
        if (!FindLockSites(mod, out o, out a, out m)) throw new Exception("LockMusicControl.CheckLockType sites not found");
        OpCode target = lockIt ? OpCodes.Ldc_I4_0 : OpCodes.Ldc_I4_1;
        if (o.OpCode == target) return false;
        o.OpCode = target;
        notes.Add("NOTE:offline:" + (lockIt ? "locked" : "open"));
        return true;
    }

    private static bool ApplyClear(ModuleDefinition mod, bool lockIt, List<string> notes)
    {
        Instruction o, a, m;
        if (!FindLockSites(mod, out o, out a, out m)) throw new Exception("LockMusicControl.CheckLockType sites not found");
        OpCode ta = lockIt ? OpCodes.Ldc_I4_0 : OpCodes.Ldc_I4_2;
        OpCode tm = lockIt ? OpCodes.Ldc_I4_0 : OpCodes.Ldc_I4_3;
        if (a.OpCode == ta && m.OpCode == tm) return false;
        a.OpCode = ta;
        m.OpCode = tm;
        notes.Add("NOTE:clear:" + (lockIt ? "locked" : "open"));
        return true;
    }

    // --- MasterList ---
    private static MethodDefinition FindMasterListLambda(ModuleDefinition mod)
    {
        var t = FindType(mod, "MusicSelectList");
        if (t == null) return null;
        foreach (var nt in t.NestedTypes)
        {
            if (!nt.Name.Contains("GetPreviewMusicInfoList")) continue;
            if (!nt.Fields.Any(f => f.Name == "musicDatabaseIDs")) continue;
            foreach (var m in nt.Methods)
            {
                if (m.Name.StartsWith("<>m__") && m.ReturnType.FullName == "System.Boolean" && m.Parameters.Count == 1)
                    return m;
            }
        }
        return null;
    }

    private static string InspectMasterList(ModuleDefinition mod)
    {
        var m = FindMasterListLambda(mod);
        if (m == null || !m.HasBody || m.Body.Instructions.Count < 2) return "unknown";
        var il = m.Body.Instructions;
        if (il[0].OpCode == OpCodes.Ldc_I4_1 && il[1].OpCode == OpCodes.Ret) return "locked";
        if (il[0].OpCode == OpCodes.Ldarg_0 && il[1].OpCode == OpCodes.Ldfld) return "open";
        return "unknown";
    }

    private static bool ApplyMasterList(ModuleDefinition mod, bool lockIt, List<string> notes)
    {
        var m = FindMasterListLambda(mod);
        if (m == null || !m.HasBody) throw new Exception("MasterList lambda not found");
        var il = m.Body.Instructions;
        bool isLocked = il.Count >= 2 && il[0].OpCode == OpCodes.Ldc_I4_1 && il[1].OpCode == OpCodes.Ret;
        if (lockIt)
        {
            if (isLocked) return false;
            var p = m.Body.GetILProcessor();
            var first = il[0];
            p.InsertBefore(first, p.Create(OpCodes.Ldc_I4_1));
            p.InsertBefore(first, p.Create(OpCodes.Ret));
            notes.Add("NOTE:masterlist:locked");
            return true;
        }
        else
        {
            if (!isLocked) return false;
            var p = m.Body.GetILProcessor();
            p.Remove(il[0]);
            p.Remove(il[0]);
            notes.Add("NOTE:masterlist:open");
            return true;
        }
    }

    // --- Coins & Gems (WeixinPlayerInfo.get_Coins / get_Gems -> 99999) ---
    private static string InspectPlayerIntProp(ModuleDefinition mod, string propName, int targetVal)
    {
        var t = FindType(mod, "TopStar.Common.WeixinPlayerInfo");
        var getter = FindMethod(t, "get_" + propName);
        if (getter == null || !getter.HasBody) return "unknown";
        var il = getter.Body.Instructions;
        if (il.Count >= 2 && il[0].OpCode == OpCodes.Ldc_I4 && (int)il[0].Operand == targetVal && il[1].OpCode == OpCodes.Ret)
            return "locked";
        if (il.Count >= 3 && il[0].OpCode == OpCodes.Ldarg_0 && il[1].OpCode == OpCodes.Ldfld && il[2].OpCode == OpCodes.Ret)
            return "open";
        return "unknown";
    }

    private static bool ApplyPlayerIntProp(ModuleDefinition mod, string key, string propName, int targetVal, bool lockIt, List<string> notes)
    {
        var t = FindType(mod, "TopStar.Common.WeixinPlayerInfo");
        if (t == null) throw new Exception("WeixinPlayerInfo not found");
        string state = InspectPlayerIntProp(mod, propName, targetVal);
        if (state == "unknown") throw new Exception("WeixinPlayerInfo." + propName + " mismatch");
        if ((lockIt && state == "locked") || (!lockIt && state == "open")) return false;
        var getter = FindMethod(t, "get_" + propName);
        var backing = t.Fields.First(f => f.Name == "<" + propName + ">k__BackingField");
        var p = getter.Body.GetILProcessor();
        getter.Body.Instructions.Clear();
        if (lockIt)
        {
            p.Append(p.Create(OpCodes.Ldc_I4, targetVal));
            p.Append(p.Create(OpCodes.Ret));
        }
        else
        {
            p.Append(p.Create(OpCodes.Ldarg_0));
            p.Append(p.Create(OpCodes.Ldfld, backing));
            p.Append(p.Create(OpCodes.Ret));
        }
        notes.Add("NOTE:" + key + ":" + (lockIt ? "locked" : "open"));
        return true;
    }

    // --- Mask helper (*CantUseMask.Awake -> gameObject.SetActive(false); ret) ---
    private static bool IsMaskHidden(ModuleDefinition mod, string typeName)
    {
        var m = FindMethod(FindType(mod, typeName), "Awake");
        if (m == null || !m.HasBody || m.Body.Instructions.Count < 5) return false;
        var il = m.Body.Instructions;
        return il[0].OpCode == OpCodes.Ldarg_0 &&
               il[1].OpCode == OpCodes.Call && il[1].Operand.ToString().Contains("get_gameObject") &&
               il[2].OpCode == OpCodes.Ldc_I4_0 &&
               il[3].OpCode == OpCodes.Callvirt && il[3].Operand.ToString().Contains("SetActive") &&
               il[4].OpCode == OpCodes.Ret;
    }

    private static void SetMaskHidden(ModuleDefinition mod, IAssemblyResolver resolver, string typeName, bool hide)
    {
        var m = FindMethod(FindType(mod, typeName), "Awake");
        if (m == null || !m.HasBody) return;
        bool currentlyHidden = IsMaskHidden(mod, typeName);
        if (hide == currentlyHidden) return;
        var il = m.Body.Instructions;
        var p = m.Body.GetILProcessor();
        if (hide)
        {
            var ue = resolver.Resolve(AssemblyNameReference.Parse("UnityEngine"));
            var compType = ue.MainModule.Types.First(x => x.FullName == "UnityEngine.Component");
            var goType = ue.MainModule.Types.First(x => x.FullName == "UnityEngine.GameObject");
            var getGo = mod.ImportReference(compType.Methods.First(x => x.Name == "get_gameObject"));
            var setActive = mod.ImportReference(goType.Methods.First(x => x.Name == "SetActive"));
            var first = il[0];
            p.InsertBefore(first, p.Create(OpCodes.Ldarg_0));
            p.InsertBefore(first, p.Create(OpCodes.Call, getGo));
            p.InsertBefore(first, p.Create(OpCodes.Ldc_I4_0));
            p.InsertBefore(first, p.Create(OpCodes.Callvirt, setActive));
            p.InsertBefore(first, p.Create(OpCodes.Ret));
        }
        else
        {
            for (int k = 0; k < 5; k++) p.Remove(il[0]);
        }
    }

    // --- Notes (PlayerInfoHelper.NoteIsUnlocked + NoteCantUseMask) ---
    private static string InspectNotes(ModuleDefinition mod)
    {
        var m = FindMethod(FindType(mod, "PlayerInfoHelper"), "NoteIsUnlocked");
        if (m == null || !m.HasBody || m.Body.Instructions.Count < 2) return "unknown";
        var il = m.Body.Instructions;
        if (il[0].OpCode == OpCodes.Ldc_I4_1 && il[1].OpCode == OpCodes.Ret) return "locked";
        if (il[0].OpCode == OpCodes.Call && il[0].Operand.ToString().Contains("OpenAllMusicPermissions")) return "open";
        return "unknown";
    }

    private static bool ApplyNotes(ModuleDefinition mod, IAssemblyResolver resolver, bool lockIt, List<string> notes)
    {
        var m = FindMethod(FindType(mod, "PlayerInfoHelper"), "NoteIsUnlocked");
        if (m == null || !m.HasBody) throw new Exception("PlayerInfoHelper.NoteIsUnlocked not found");
        var il = m.Body.Instructions;
        bool isLocked = il.Count >= 2 && il[0].OpCode == OpCodes.Ldc_I4_1 && il[1].OpCode == OpCodes.Ret;
        bool maskHidden = IsMaskHidden(mod, "NoteCantUseMask");
        if (lockIt)
        {
            if (isLocked && maskHidden) return false;
            if (!isLocked)
            {
                var p = m.Body.GetILProcessor();
                var first = il[0];
                p.InsertBefore(first, p.Create(OpCodes.Ldc_I4_1));
                p.InsertBefore(first, p.Create(OpCodes.Ret));
            }
            SetMaskHidden(mod, resolver, "NoteCantUseMask", true);
            notes.Add("NOTE:notes:locked");
            return true;
        }
        else
        {
            if (!isLocked && !maskHidden) return false;
            if (isLocked)
            {
                var p = m.Body.GetILProcessor();
                p.Remove(il[0]);
                p.Remove(il[0]);
            }
            SetMaskHidden(mod, resolver, "NoteCantUseMask", false);
            notes.Add("NOTE:notes:open");
            return true;
        }
    }

    // --- Items (WeixinPlayerInfo 18 properties) ---
    private static string InspectItems(ModuleDefinition mod)
    {
        var t = FindType(mod, "TopStar.Common.WeixinPlayerInfo");
        if (t == null) return "unknown";
        bool anyOpen = false, anyLocked = false;
        foreach (var name in ItemPropNames)
        {
            var getter = FindMethod(t, "get_" + name);
            if (getter == null || !getter.HasBody) return "unknown";
            var il = getter.Body.Instructions;
            if (il.Count >= 2 && il[0].OpCode == OpCodes.Ldc_I4 && (int)il[0].Operand == 999 && il[1].OpCode == OpCodes.Ret)
                anyLocked = true;
            else if (il.Count >= 3 && il[0].OpCode == OpCodes.Ldarg_0 && il[1].OpCode == OpCodes.Ldfld && il[2].OpCode == OpCodes.Ret)
                anyOpen = true;
            else
                return "unknown";
        }
        if (anyLocked && anyOpen) return "unknown";
        return anyLocked ? "locked" : "open";
    }

    private static bool ApplyItems(ModuleDefinition mod, IAssemblyResolver resolver, bool lockIt, List<string> notes)
    {
        var t = FindType(mod, "TopStar.Common.WeixinPlayerInfo");
        if (t == null) throw new Exception("WeixinPlayerInfo not found");
        string state = InspectItems(mod);
        if (state == "unknown") throw new Exception("WeixinPlayerInfo items mismatch");
        bool masksHidden = IsMaskHidden(mod, "GuestCantUseMask") &&
                           IsMaskHidden(mod, "ShieldCantUseMask") &&
                           IsMaskHidden(mod, "PropCantUseMask");
        if (lockIt && state == "locked" && masksHidden) return false;
        if (!lockIt && state == "open" && !IsMaskHidden(mod, "GuestCantUseMask") && !IsMaskHidden(mod, "ShieldCantUseMask") && !IsMaskHidden(mod, "PropCantUseMask")) return false;
        if ((lockIt && state != "locked") || (!lockIt && state != "open"))
        {
            foreach (var name in ItemPropNames)
            {
                var getter = FindMethod(t, "get_" + name);
                var backing = t.Fields.First(f => f.Name == "<" + name + ">k__BackingField");
                var p = getter.Body.GetILProcessor();
                getter.Body.Instructions.Clear();
                if (lockIt)
                {
                    p.Append(p.Create(OpCodes.Ldc_I4, 999));
                    p.Append(p.Create(OpCodes.Ret));
                }
                else
                {
                    p.Append(p.Create(OpCodes.Ldarg_0));
                    p.Append(p.Create(OpCodes.Ldfld, backing));
                    p.Append(p.Create(OpCodes.Ret));
                }
            }
        }
        SetMaskHidden(mod, resolver, "GuestCantUseMask", lockIt);
        SetMaskHidden(mod, resolver, "ShieldCantUseMask", lockIt);
        SetMaskHidden(mod, resolver, "PropCantUseMask", lockIt);
        notes.Add("NOTE:items:" + (lockIt ? "locked" : "open"));
        return true;
    }

    // --- GameOver Return (ContinueControl) ---
    private static string InspectGameOverReturn(ModuleDefinition mod)
    {
        var t = FindType(mod, "ContinueControl");
        if (t == null) return "unknown";
        return t.Fields.Any(f => f.Name == "_autoReturnStartTime") ? "locked" : "open";
    }

    private static bool ApplyGameOverReturn(ModuleDefinition mod, IAssemblyResolver resolver, bool lockIt, List<string> notes)
    {
        var t = FindType(mod, "ContinueControl");
        if (t == null) throw new Exception("ContinueControl not found");
        bool isLocked = t.Fields.Any(f => f.Name == "_autoReturnStartTime");
        if (!lockIt)
        {
            if (!isLocked) return false;
            // Cannot easily revert or we can leave it if not requested, but actually we CAN revert it cleanly!
            var f1 = t.Fields.First(f => f.Name == "_autoReturnStartTime");
            var f2 = t.Fields.First(f => f.Name == "_enteringTitle");
            var upd = FindMethod(t, "Update");
            if (upd != null) t.Methods.Remove(upd);
            var awake = FindMethod(t, "Awake");
            if (awake != null && awake.HasBody)
            {
                var il = awake.Body.Instructions;
                for (int i = il.Count - 1; i >= 0; i--)
                {
                    if ((il[i].OpCode == OpCodes.Stfld) && (il[i].Operand == f1 || il[i].Operand == f2))
                    {
                        if (i >= 2 && il[i - 2].OpCode == OpCodes.Ldarg_0)
                        {
                            il.RemoveAt(i); il.RemoveAt(i - 1); il.RemoveAt(i - 2);
                            i -= 2;
                        }
                    }
                }
            }
            var enter = FindMethod(t, "EnterTitle_NguiCallback");
            if (enter != null && enter.HasBody)
            {
                var il = enter.Body.Instructions;
                for (int i = il.Count - 1; i >= 0; i--)
                {
                    if ((il[i].OpCode == OpCodes.Stfld) && (il[i].Operand == f1 || il[i].Operand == f2))
                    {
                        if (i >= 2 && il[i - 2].OpCode == OpCodes.Ldarg_0)
                        {
                            il.RemoveAt(i); il.RemoveAt(i - 1); il.RemoveAt(i - 2);
                            i -= 2;
                        }
                    }
                }
            }
            t.Fields.Remove(f1);
            t.Fields.Remove(f2);
            notes.Add("NOTE:gameover_return:open");
            return true;
        }
        if (isLocked) return false;

        var isClickedField = t.Fields.First(f => f.Name == "isClicked");
        var awakeMethod = FindMethod(t, "Awake");
        var enterTitleMethod = FindMethod(t, "EnterTitle_NguiCallback");
        var ue = resolver.Resolve(AssemblyNameReference.Parse("UnityEngine"));
        var timeType = ue.MainModule.Types.First(x => x.FullName == "UnityEngine.Time");
        var getRealtime = mod.ImportReference(timeType.Methods.First(x => x.Name == "get_realtimeSinceStartup"));
        var titleType = t.NestedTypes.First(x => x.Name.Contains("Title"));
        var moveNext = FindMethod(titleType, "MoveNext");
        MethodReference getInstance = null, loadLevel = null;
        foreach (var ins in moveNext.Body.Instructions)
        {
            if ((ins.OpCode == OpCodes.Call || ins.OpCode == OpCodes.Callvirt) && ins.Operand is MethodReference)
            {
                var mr = (MethodReference)ins.Operand;
                if (mr.Name == "get_Instance" && mr.DeclaringType.FullName.Contains("SceneManager")) getInstance = mr;
                else if (mr.Name == "LoadLevel" && mr.DeclaringType.Name == "SceneManager") loadLevel = mr;
            }
        }
        if (getInstance == null || loadLevel == null) throw new Exception("SceneManager.Instance.LoadLevel not found");

        var fStart = new FieldDefinition("_autoReturnStartTime", FieldAttributes.Private, mod.TypeSystem.Single);
        var fEnter = new FieldDefinition("_enteringTitle", FieldAttributes.Private, mod.TypeSystem.Boolean);
        t.Fields.Add(fStart);
        t.Fields.Add(fEnter);

        var pAwake = awakeMethod.Body.GetILProcessor();
        var awakeLast = awakeMethod.Body.Instructions.Last();
        pAwake.InsertBefore(awakeLast, pAwake.Create(OpCodes.Ldarg_0));
        pAwake.InsertBefore(awakeLast, pAwake.Create(OpCodes.Call, getRealtime));
        pAwake.InsertBefore(awakeLast, pAwake.Create(OpCodes.Stfld, fStart));
        pAwake.InsertBefore(awakeLast, pAwake.Create(OpCodes.Ldarg_0));
        pAwake.InsertBefore(awakeLast, pAwake.Create(OpCodes.Ldc_I4_0));
        pAwake.InsertBefore(awakeLast, pAwake.Create(OpCodes.Stfld, fEnter));

        var pEnter = enterTitleMethod.Body.GetILProcessor();
        var enterFirst = enterTitleMethod.Body.Instructions.First();
        pEnter.InsertBefore(enterFirst, pEnter.Create(OpCodes.Ldarg_0));
        pEnter.InsertBefore(enterFirst, pEnter.Create(OpCodes.Ldc_I4_1));
        pEnter.InsertBefore(enterFirst, pEnter.Create(OpCodes.Stfld, fEnter));
        pEnter.InsertBefore(enterFirst, pEnter.Create(OpCodes.Ldarg_0));
        pEnter.InsertBefore(enterFirst, pEnter.Create(OpCodes.Call, getRealtime));
        pEnter.InsertBefore(enterFirst, pEnter.Create(OpCodes.Stfld, fStart));

        var updMethod = new MethodDefinition("Update", MethodAttributes.Private | MethodAttributes.HideBySig, mod.TypeSystem.Void);
        updMethod.Body.InitLocals = true;
        var elapsed = new VariableDefinition(mod.TypeSystem.Single);
        updMethod.Body.Variables.Add(elapsed);
        var behType = ue.MainModule.Types.First(x => x.FullName == "UnityEngine.Behaviour");
        var setEnabled = mod.ImportReference(behType.Methods.First(x => x.Name == "set_enabled"));

        var pUpd = updMethod.Body.GetILProcessor();
        var lblInitDone = pUpd.Create(OpCodes.Nop);
        var lblCheckEnter = pUpd.Create(OpCodes.Nop);
        var lblRet = pUpd.Create(OpCodes.Ret);

        pUpd.Append(pUpd.Create(OpCodes.Ldarg_0));
        pUpd.Append(pUpd.Create(OpCodes.Ldfld, fStart));
        pUpd.Append(pUpd.Create(OpCodes.Ldc_R4, 0f));
        pUpd.Append(pUpd.Create(OpCodes.Bgt_Un_S, lblInitDone));
        pUpd.Append(pUpd.Create(OpCodes.Ldarg_0));
        pUpd.Append(pUpd.Create(OpCodes.Call, getRealtime));
        pUpd.Append(pUpd.Create(OpCodes.Stfld, fStart));
        pUpd.Append(pUpd.Create(OpCodes.Ret));
        pUpd.Append(lblInitDone);
        pUpd.Append(pUpd.Create(OpCodes.Call, getRealtime));
        pUpd.Append(pUpd.Create(OpCodes.Ldarg_0));
        pUpd.Append(pUpd.Create(OpCodes.Ldfld, fStart));
        pUpd.Append(pUpd.Create(OpCodes.Sub));
        pUpd.Append(pUpd.Create(OpCodes.Stloc, elapsed));
        pUpd.Append(pUpd.Create(OpCodes.Ldarg_0));
        pUpd.Append(pUpd.Create(OpCodes.Ldfld, isClickedField));
        pUpd.Append(pUpd.Create(OpCodes.Brtrue_S, lblCheckEnter));
        pUpd.Append(pUpd.Create(OpCodes.Ldloc, elapsed));
        pUpd.Append(pUpd.Create(OpCodes.Ldc_R4, 20f));
        pUpd.Append(pUpd.Create(OpCodes.Blt_Un_S, lblRet));
        pUpd.Append(pUpd.Create(OpCodes.Ldarg_0));
        pUpd.Append(pUpd.Create(OpCodes.Call, enterTitleMethod));
        pUpd.Append(pUpd.Create(OpCodes.Ret));
        pUpd.Append(lblCheckEnter);
        pUpd.Append(pUpd.Create(OpCodes.Ldarg_0));
        pUpd.Append(pUpd.Create(OpCodes.Ldfld, fEnter));
        pUpd.Append(pUpd.Create(OpCodes.Brfalse_S, lblRet));
        pUpd.Append(pUpd.Create(OpCodes.Ldloc, elapsed));
        pUpd.Append(pUpd.Create(OpCodes.Ldc_R4, 4f));
        pUpd.Append(pUpd.Create(OpCodes.Blt_Un_S, lblRet));
        pUpd.Append(pUpd.Create(OpCodes.Call, getInstance));
        pUpd.Append(pUpd.Create(OpCodes.Ldstr, "Title"));
        pUpd.Append(pUpd.Create(OpCodes.Callvirt, loadLevel));
        pUpd.Append(pUpd.Create(OpCodes.Ldarg_0));
        pUpd.Append(pUpd.Create(OpCodes.Ldc_I4_0));
        pUpd.Append(pUpd.Create(OpCodes.Call, setEnabled));
        pUpd.Append(lblRet);
        t.Methods.Add(updMethod);

        notes.Add("NOTE:gameover_return:locked");
        return true;
    }

    // --- No IO Detection (PcbManager) ---
    private static string InspectNoIo(ModuleDefinition mod)
    {
        var t = FindType(mod, "PcbManager");
        if (t == null) return "unknown";
        var init = FindMethod(t, "PCBLib_Init");
        if (init == null) return "unknown";
        return init.HasPInvokeInfo ? "open" : "locked";
    }

    private static bool ApplyNoIo(ModuleDefinition mod, IAssemblyResolver resolver, bool lockIt, List<string> notes)
    {
        var t = FindType(mod, "PcbManager");
        if (t == null) throw new Exception("PcbManager not found");
        bool isLocked = !FindMethod(t, "PCBLib_Init").HasPInvokeInfo;
        if (lockIt == isLocked) return false;

        if (lockIt)
        {
            var ue = resolver.Resolve(AssemblyNameReference.Parse("UnityEngine"));
            var inputType = ue.MainModule.Types.First(x => x.FullName == "UnityEngine.Input");
            var keyCodeType = ue.MainModule.Types.First(x => x.FullName == "UnityEngine.KeyCode");
            var getKey = mod.ImportReference(inputType.Methods.First(x =>
                x.Name == "GetKey" && x.Parameters.Count == 1 && x.Parameters[0].ParameterType.FullName == "UnityEngine.KeyCode"));

            foreach (var m in t.Methods)
            {
                if (!PcbEntryPoints.ContainsKey(m.Name)) continue;
                m.PInvokeInfo = null;
                m.IsPInvokeImpl = false;
                m.IsPreserveSig = false;
                m.ImplAttributes = MethodImplAttributes.IL;
                m.Body = new MethodBody(m);
                var p = m.Body.GetILProcessor();

                if (m.Name == "PCBLib_Init" || m.Name == "PCBLib_IsConnect")
                {
                    p.Append(p.Create(OpCodes.Ldc_I4_1));
                    p.Append(p.Create(OpCodes.Ret));
                }
                else if (m.Name == "PCBLib_GetStatus1")
                {
                    p.Append(p.Create(OpCodes.Ldc_I4, 282)); // KeyCode.F1
                    p.Append(p.Create(OpCodes.Call, getKey));
                    p.Append(p.Create(OpCodes.Ldc_I4, 283)); // KeyCode.F2
                    p.Append(p.Create(OpCodes.Call, getKey));
                    p.Append(p.Create(OpCodes.Ldc_I4_4));
                    p.Append(p.Create(OpCodes.Mul));
                    p.Append(p.Create(OpCodes.Or));
                    p.Append(p.Create(OpCodes.Ret));
                }
                else if (m.ReturnType.FullName == "System.Void")
                {
                    p.Append(p.Create(OpCodes.Ret));
                }
                else if (m.ReturnType.FullName == "System.UInt64")
                {
                    p.Append(p.Create(OpCodes.Ldc_I4_0));
                    p.Append(p.Create(OpCodes.Conv_I8));
                    p.Append(p.Create(OpCodes.Ret));
                }
                else
                {
                    p.Append(p.Create(OpCodes.Ldc_I4_0));
                    p.Append(p.Create(OpCodes.Ret));
                }
            }
            notes.Add("NOTE:no_io:locked");
        }
        else
        {
            var pcbMod = mod.ModuleReferences.FirstOrDefault(mr => mr.Name == "PCBLib");
            if (pcbMod == null)
            {
                pcbMod = new ModuleReference("PCBLib");
                mod.ModuleReferences.Add(pcbMod);
            }
            foreach (var m in t.Methods)
            {
                string ep;
                if (!PcbEntryPoints.TryGetValue(m.Name, out ep)) continue;
                m.Body = null;
                m.IsPInvokeImpl = true;
                m.IsPreserveSig = true;
                m.ImplAttributes = MethodImplAttributes.IL | MethodImplAttributes.PreserveSig;
                m.PInvokeInfo = new PInvokeInfo(PInvokeAttributes.CallConvWinapi, ep, pcbMod);
            }
            notes.Add("NOTE:no_io:open");
        }
        return true;
    }

    // --- Free Play (ManagerDbSetting.get_IsFreePlay) ---
    private static string InspectFreePlay(ModuleDefinition mod)
    {
        var m = FindMethod(FindType(mod, "ManagerDbSetting"), "get_IsFreePlay");
        if (m == null || !m.HasBody || m.Body.Instructions.Count < 2) return "unknown";
        var il = m.Body.Instructions;
        if (il[0].OpCode == OpCodes.Ldc_I4_1 && il[1].OpCode == OpCodes.Ret) return "locked";
        return "open";
    }

    private static bool ApplyFreePlay(ModuleDefinition mod, bool lockIt, List<string> notes)
    {
        var m = FindMethod(FindType(mod, "ManagerDbSetting"), "get_IsFreePlay");
        if (m == null || !m.HasBody) throw new Exception("ManagerDbSetting.get_IsFreePlay not found");
        var il = m.Body.Instructions;
        bool isLocked = il.Count >= 2 && il[0].OpCode == OpCodes.Ldc_I4_1 && il[1].OpCode == OpCodes.Ret;
        if (lockIt)
        {
            if (isLocked) return false;
            var p = m.Body.GetILProcessor();
            var first = il[0];
            p.InsertBefore(first, p.Create(OpCodes.Ldc_I4_1));
            p.InsertBefore(first, p.Create(OpCodes.Ret));
            notes.Add("NOTE:free_play:locked");
            return true;
        }
        else
        {
            if (!isLocked) return false;
            var p = m.Body.GetILProcessor();
            p.Remove(il[0]);
            p.Remove(il[0]);
            notes.Add("NOTE:free_play:open");
            return true;
        }
    }

    // --- Fix Touch / Mouse (SystemTouchInput.Init -> false, TouchInputFactory.get_TouchIsConnection -> TouchInput.IsConnection, and use PortableWindowsTouch if available) ---
    private static string InspectFixTouch(ModuleDefinition mod)
    {
        var mInit = FindMethod(FindType(mod, "SystemTouchInput"), "Init");
        var tFactory = FindType(mod, "TouchInputFactory");
        var mConn = FindMethod(tFactory, "get_TouchIsConnection");
        var mGet = FindMethod(tFactory, "get_TouchInput");
        if (mInit == null || !mInit.HasBody || mInit.Body.Instructions.Count < 2) return "unknown";
        if (mConn == null || !mConn.HasBody || mConn.Body.Instructions.Count < 2) return "unknown";
        if (mGet == null || !mGet.HasBody) return "unknown";
        var ilInit = mInit.Body.Instructions;
        var ilConn = mConn.Body.Instructions;
        bool initLocked = ilInit[0].OpCode == OpCodes.Ldc_I4_0 && ilInit[1].OpCode == OpCodes.Ret;
        bool connLocked = ilConn[0].OpCode == OpCodes.Ldarg_0 && ilConn[1].OpCode == OpCodes.Call &&
                          ilConn[1].Operand.ToString().Contains("get_TouchInput");
        bool wtLocked = mGet.Body.Instructions.Any(i => i.OpCode == OpCodes.Newobj && i.Operand.ToString().Contains("WindowsTouchInput"));
        if (initLocked && connLocked && wtLocked) return "locked";
        if (!initLocked && !connLocked && !wtLocked) return "open";
        return "unknown";
    }

    private static bool ApplyFixTouch(ModuleDefinition mod, IAssemblyResolver resolver, bool lockIt, List<string> notes)
    {
        var mInit = FindMethod(FindType(mod, "SystemTouchInput"), "Init");
        var tFactory = FindType(mod, "TouchInputFactory");
        var mConn = FindMethod(tFactory, "get_TouchIsConnection");
        var mGet = FindMethod(tFactory, "get_TouchInput");
        var mGetTouchInput = mGet;
        var iTouchType = FindType(mod, "ITouchInput");
        var mGetIsConn = FindMethod(iTouchType, "get_IsConnection");
        var fTouchInput = tFactory == null ? null : tFactory.Fields.FirstOrDefault(f => f.Name == "touchInput");
        if (mInit == null || !mInit.HasBody || mConn == null || !mConn.HasBody || mGet == null || !mGet.HasBody || mGetIsConn == null || fTouchInput == null)
            throw new Exception("TouchInputFactory/SystemTouchInput methods not found");

        var ilInit = mInit.Body.Instructions;
        var ilConn = mConn.Body.Instructions;
        bool initLocked = ilInit.Count >= 2 && ilInit[0].OpCode == OpCodes.Ldc_I4_0 && ilInit[1].OpCode == OpCodes.Ret;
        bool connLocked = ilConn.Count >= 4 && ilConn[0].OpCode == OpCodes.Ldarg_0 &&
                          ilConn[1].OpCode == OpCodes.Call && ilConn[1].Operand.ToString().Contains("get_TouchInput");
        bool wtLocked = mGet.Body.Instructions.Any(i => i.OpCode == OpCodes.Newobj && i.Operand.ToString().Contains("WindowsTouchInput"));

        if (lockIt)
        {
            if (initLocked && connLocked && wtLocked) return false;
            if (!initLocked)
            {
                var p = mInit.Body.GetILProcessor();
                var first = ilInit[0];
                p.InsertBefore(first, p.Create(OpCodes.Ldc_I4_0));
                p.InsertBefore(first, p.Create(OpCodes.Ret));
            }
            if (!connLocked)
            {
                var p = mConn.Body.GetILProcessor();
                var first = ilConn[0];
                p.InsertBefore(first, p.Create(OpCodes.Ldarg_0));
                p.InsertBefore(first, p.Create(OpCodes.Call, mGetTouchInput));
                p.InsertBefore(first, p.Create(OpCodes.Callvirt, mGetIsConn));
                p.InsertBefore(first, p.Create(OpCodes.Ret));
            }
            if (!wtLocked)
            {
                AssemblyDefinition pwtAsm = null;
                TypeDefinition wtType = null;
                try
                {
                    pwtAsm = resolver.Resolve(AssemblyNameReference.Parse("PortableWindowsTouch"));
                    wtType = pwtAsm.MainModule.Types.FirstOrDefault(x => x.Name == "WindowsTouchInput");
                }
                catch { }
                if (wtType == null)
                {
                    string localPwt = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "PortableWindowsTouch.dll");
                    if (File.Exists(localPwt))
                    {
                        pwtAsm = AssemblyDefinition.ReadAssembly(localPwt);
                        wtType = pwtAsm.MainModule.Types.FirstOrDefault(x => x.Name == "WindowsTouchInput");
                    }
                }
                if (wtType == null) throw new Exception("WindowsTouchInput not found in PortableWindowsTouch.dll");
                var wtCtor = mod.ImportReference(wtType.Methods.First(x => x.IsConstructor && x.Parameters.Count == 0));
                var wtInit = mod.ImportReference(wtType.Methods.First(x => x.Name == "Init"));
                var wtVar = new VariableDefinition(mod.ImportReference(wtType));
                mGet.Body.InitLocals = true;
                mGet.Body.Variables.Add(wtVar);

                // Find instruction after `if (touchInput != null) return touchInput;` (i.e. `newobj VirtualTouchInput`)
                var ilGet = mGet.Body.Instructions;
                Instruction insertTarget = ilGet.FirstOrDefault(i => i.OpCode == OpCodes.Newobj && i.Operand.ToString().Contains("VirtualTouchInput"));
                if (insertTarget == null) throw new Exception("VirtualTouchInput creation not found in get_TouchInput");

                var p = mGet.Body.GetILProcessor();
                var firstNew = p.Create(OpCodes.Newobj, wtCtor);
                foreach (var ins in ilGet.ToArray())
                {
                    if (ins.Operand == insertTarget) ins.Operand = firstNew;
                }
                p.InsertBefore(insertTarget, firstNew);
                p.InsertBefore(insertTarget, p.Create(OpCodes.Stloc, wtVar));
                p.InsertBefore(insertTarget, p.Create(OpCodes.Ldloc, wtVar));
                p.InsertBefore(insertTarget, p.Create(OpCodes.Callvirt, wtInit));
                p.InsertBefore(insertTarget, p.Create(OpCodes.Brfalse_S, insertTarget));
                p.InsertBefore(insertTarget, p.Create(OpCodes.Ldarg_0));
                p.InsertBefore(insertTarget, p.Create(OpCodes.Ldloc, wtVar));
                p.InsertBefore(insertTarget, p.Create(OpCodes.Stfld, fTouchInput));
                p.InsertBefore(insertTarget, p.Create(OpCodes.Ldloc, wtVar));
                p.InsertBefore(insertTarget, p.Create(OpCodes.Ret));
            }
            notes.Add("NOTE:fix_touch:locked");
            return true;
        }
        else
        {
            if (!initLocked && !connLocked && !wtLocked) return false;
            if (initLocked)
            {
                var p = mInit.Body.GetILProcessor();
                p.Remove(ilInit[0]);
                p.Remove(ilInit[0]);
            }
            if (connLocked)
            {
                var p = mConn.Body.GetILProcessor();
                p.Remove(ilConn[0]);
                p.Remove(ilConn[0]);
                p.Remove(ilConn[0]);
                p.Remove(ilConn[0]);
            }
            if (wtLocked)
            {
                var ilGet = mGet.Body.Instructions;
                for (int i = 0; i < ilGet.Count; i++)
                {
                    if (ilGet[i].OpCode == OpCodes.Newobj && ilGet[i].Operand.ToString().Contains("WindowsTouchInput"))
                    {
                        var firstNew = ilGet[i];
                        var targetAfter = ilGet[i + 10];
                        foreach (var ins in ilGet.ToArray())
                        {
                            if (ins.Operand == firstNew) ins.Operand = targetAfter;
                        }
                        var p = mGet.Body.GetILProcessor();
                        for (int k = 0; k < 10; k++) p.Remove(ilGet[i]);
                        break;
                    }
                }
            }
            notes.Add("NOTE:fix_touch:open");
            return true;
        }
    }

    private static int FindFpsDisplayIndex(MethodDefinition m)
    {
        if (m == null || !m.HasBody) return -1;
        var il = m.Body.Instructions;
        for (int i = 0; i < il.Count - 1; i++)
        {
            if (il[i].OpCode == OpCodes.Call &&
                il[i].Operand.ToString().Contains("SingletonObject`1<FPSCounter>::get_Instance") &&
                il[i + 1].OpCode == OpCodes.Pop)
            {
                return i;
            }
        }
        return -1;
    }

    private static string InspectFpsDisplay(ModuleDefinition mod)
    {
        var plrStart = FindMethod(FindType(mod, "PreLoadResource"), "Start");
        if (plrStart == null || !plrStart.HasBody) return "unknown";
        return FindFpsDisplayIndex(plrStart) >= 0 ? "locked" : "open";
    }

    private static bool ApplyFpsDisplay(ModuleDefinition mod, bool lockIt, List<string> notes)
    {
        var plrStart = FindMethod(FindType(mod, "PreLoadResource"), "Start");
        if (plrStart == null || !plrStart.HasBody) throw new Exception("PreLoadResource.Start not found");
        int idx = FindFpsDisplayIndex(plrStart);
        bool isLocked = idx >= 0;
        if (lockIt)
        {
            if (isLocked) return false;
            var fpsType = FindType(mod, "FPSCounter");
            if (fpsType == null) throw new Exception("FPSCounter type not found");
            var singletonBase = fpsType.BaseType as GenericInstanceType;
            if (singletonBase == null) throw new Exception("FPSCounter base type is not GenericInstanceType");
            var baseDef = singletonBase.ElementType.Resolve();
            var getInstDef = baseDef.Methods.FirstOrDefault(x => x.Name == "get_Instance");
            if (getInstDef == null) throw new Exception("SingletonObject.get_Instance not found");

            var getInstRef = new MethodReference(getInstDef.Name, getInstDef.ReturnType, singletonBase)
            {
                HasThis = false
            };

            var il = plrStart.Body.Instructions;
            var retIns = il[il.Count - 1];
            if (retIns.OpCode != OpCodes.Ret) throw new Exception("Unexpected PreLoadResource.Start tail");
            var p = plrStart.Body.GetILProcessor();
            p.InsertBefore(retIns, p.Create(OpCodes.Call, mod.ImportReference(getInstRef)));
            p.InsertBefore(retIns, p.Create(OpCodes.Pop));
            notes.Add("NOTE:fps_display:locked");
            return true;
        }
        else
        {
            if (!isLocked) return false;
            var il = plrStart.Body.Instructions;
            var p = plrStart.Body.GetILProcessor();
            p.Remove(il[idx]);
            p.Remove(il[idx]);
            notes.Add("NOTE:fps_display:open");
            return true;
        }
    }

    private static int FindCallPair(MethodDefinition m, string methodSubstr)
    {
        if (m == null || !m.HasBody) return -1;
        var il = m.Body.Instructions;
        for (int i = 0; i < il.Count - 1; i++)
        {
            if ((il[i].OpCode == OpCodes.Ldc_I4 || il[i].OpCode == OpCodes.Ldc_I4_0) &&
                il[i + 1].OpCode == OpCodes.Call &&
                il[i + 1].Operand.ToString().Contains(methodSubstr))
            {
                return i;
            }
        }
        return -1;
    }

    private static int FindSetResIdx(MethodDefinition m, bool withRefreshRate)
    {
        if (m == null || !m.HasBody) return -1;
        string sig = withRefreshRate
            ? "Screen::SetResolution(System.Int32,System.Int32,System.Boolean,System.Int32)"
            : "Screen::SetResolution(System.Int32,System.Int32,System.Boolean)";
        var il = m.Body.Instructions;
        for (int i = 0; i < il.Count; i++)
        {
            if (il[i].OpCode == OpCodes.Call && il[i].Operand.ToString().Contains(sig))
                return i;
        }
        return -1;
    }

    private static string InspectFps(ModuleDefinition mod)
    {
        var plrStart = FindMethod(FindType(mod, "PreLoadResource"), "Start");
        var escSet = FindMethod(FindType(mod, "Esc"), "SetFullScreen");
        if (plrStart == null || !plrStart.HasBody || escSet == null || !escSet.HasBody) return "unknown";

        var pIl = plrStart.Body.Instructions;
        var eIl = escSet.Body.Instructions;
        int pFpsIdx = FindCallPair(plrStart, "set_targetFrameRate");
        int eRes3Idx = FindSetResIdx(escSet, false);
        int eRes4Idx = FindSetResIdx(escSet, true);

        if (pFpsIdx < 0 && eRes3Idx >= 0) return "open|60";
        if (pFpsIdx >= 0 && eRes4Idx >= 1 && eIl[eRes4Idx - 1].OpCode == OpCodes.Ldc_I4)
        {
            int fps1 = (int)pIl[pFpsIdx].Operand;
            int fps2 = (int)eIl[eRes4Idx - 1].Operand;
            if (fps1 == fps2 && fps1 > 0) return "locked|" + fps1;
        }
        return "unknown";
    }

    private static string InspectVsync(ModuleDefinition mod)
    {
        var plrStart = FindMethod(FindType(mod, "PreLoadResource"), "Start");
        var escSet = FindMethod(FindType(mod, "Esc"), "SetFullScreen");
        if (plrStart == null || !plrStart.HasBody || escSet == null || !escSet.HasBody) return "unknown";

        int pVsIdx = FindCallPair(plrStart, "set_vSyncCount");
        int eVsIdx = FindCallPair(escSet, "set_vSyncCount");
        if (pVsIdx >= 0 && eVsIdx >= 0) return "locked";
        if (pVsIdx < 0 && eVsIdx < 0) return "open";
        return "unknown";
    }

    private static MethodReference ResolveUnityMethod(ModuleDefinition mod, IAssemblyResolver resolver, string typeFullName, string methodName, int paramCount)
    {
        foreach (var r in mod.AssemblyReferences)
        {
            if (r.Name == "UnityEngine")
            {
                var ue = resolver.Resolve(r);
                var tt = ue.MainModule.Types.First(x => x.FullName == typeFullName);
                var m = tt.Methods.FirstOrDefault(x => x.Name == methodName && x.Parameters.Count == paramCount);
                if (m != null) return mod.ImportReference(m);
            }
        }
        throw new Exception(typeFullName + "." + methodName + "(" + paramCount + ") not found");
    }

    private static bool ApplyVsync(ModuleDefinition mod, IAssemblyResolver resolver, bool lockIt, List<string> notes)
    {
        var plrStart = FindMethod(FindType(mod, "PreLoadResource"), "Start");
        var escSet = FindMethod(FindType(mod, "Esc"), "SetFullScreen");
        if (plrStart == null || !plrStart.HasBody || escSet == null || !escSet.HasBody)
            throw new Exception("PreLoadResource.Start or Esc.SetFullScreen not found");

        var pIl = plrStart.Body.Instructions;
        var eIl = escSet.Body.Instructions;
        int pVsIdx = FindCallPair(plrStart, "set_vSyncCount");
        int eVsIdx = FindCallPair(escSet, "set_vSyncCount");

        if (lockIt)
        {
            if (pVsIdx >= 0 && eVsIdx >= 0) return false;
            var setVSync = ResolveUnityMethod(mod, resolver, "UnityEngine.QualitySettings", "set_vSyncCount", 1);
            if (pVsIdx < 0)
            {
                var pp = plrStart.Body.GetILProcessor();
                var first = pIl[0];
                pp.InsertBefore(first, pp.Create(OpCodes.Ldc_I4_0));
                pp.InsertBefore(first, pp.Create(OpCodes.Call, setVSync));
            }
            if (eVsIdx < 0)
            {
                var ep = escSet.Body.GetILProcessor();
                var retIns = eIl[eIl.Count - 1];
                ep.InsertBefore(retIns, ep.Create(OpCodes.Ldc_I4_0));
                ep.InsertBefore(retIns, ep.Create(OpCodes.Call, setVSync));
            }
            notes.Add("NOTE:vsync_off:locked");
            return true;
        }
        else
        {
            if (pVsIdx < 0 && eVsIdx < 0) return false;
            if (pVsIdx >= 0)
            {
                var pp = plrStart.Body.GetILProcessor();
                pp.Remove(pIl[pVsIdx + 1]);
                pp.Remove(pIl[pVsIdx]);
            }
            if (eVsIdx >= 0)
            {
                var ep = escSet.Body.GetILProcessor();
                ep.Remove(eIl[eVsIdx + 1]);
                ep.Remove(eIl[eVsIdx]);
            }
            notes.Add("NOTE:vsync_off:open");
            return true;
        }
    }

    private static bool ApplyFps(ModuleDefinition mod, IAssemblyResolver resolver, bool lockIt, int fps, List<string> notes)
    {
        var plrStart = FindMethod(FindType(mod, "PreLoadResource"), "Start");
        var escSet = FindMethod(FindType(mod, "Esc"), "SetFullScreen");
        if (plrStart == null || !plrStart.HasBody || escSet == null || !escSet.HasBody)
            throw new Exception("PreLoadResource.Start or Esc.SetFullScreen not found");

        var pIl = plrStart.Body.Instructions;
        var eIl = escSet.Body.Instructions;
        int pFpsIdx = FindCallPair(plrStart, "set_targetFrameRate");
        int eFpsIdx = FindCallPair(escSet, "set_targetFrameRate");
        int eRes4Idx = FindSetResIdx(escSet, true);
        int eRes3Idx = FindSetResIdx(escSet, false);
        bool plrLocked = pFpsIdx >= 0;
        bool escLocked = eRes4Idx >= 1 && eIl[eRes4Idx - 1].OpCode == OpCodes.Ldc_I4;

        if (lockIt)
        {
            if (fps < 60 || fps > 1000) throw new Exception("Invalid FPS: " + fps);
            if (plrLocked && escLocked && (int)pIl[pFpsIdx].Operand == fps && (int)eIl[eRes4Idx - 1].Operand == fps)
                return false;

            var setTargetFps = ResolveUnityMethod(mod, resolver, "UnityEngine.Application", "set_targetFrameRate", 1);
            var setRes4 = ResolveUnityMethod(mod, resolver, "UnityEngine.Screen", "SetResolution", 4);

            var pp = plrStart.Body.GetILProcessor();
            if (!plrLocked)
            {
                var first = pIl[0];
                pp.InsertBefore(first, pp.Create(OpCodes.Ldc_I4, fps));
                pp.InsertBefore(first, pp.Create(OpCodes.Call, setTargetFps));
            }
            else
            {
                pIl[pFpsIdx].Operand = fps;
            }

            var ep = escSet.Body.GetILProcessor();
            if (escLocked)
            {
                eIl[eRes4Idx - 1].Operand = fps;
                if (eFpsIdx >= 0)
                {
                    eIl[eFpsIdx].Operand = fps;
                }
                else
                {
                    var retIns = eIl[eIl.Count - 1];
                    ep.InsertBefore(retIns, ep.Create(OpCodes.Ldc_I4, fps));
                    ep.InsertBefore(retIns, ep.Create(OpCodes.Call, setTargetFps));
                }
            }
            else
            {
                if (eRes3Idx < 0) throw new Exception("Unexpected Esc.SetFullScreen IL");
                var oldCall = eIl[eRes3Idx];
                ep.InsertBefore(oldCall, ep.Create(OpCodes.Ldc_I4, fps));
                ep.InsertBefore(oldCall, ep.Create(OpCodes.Call, setRes4));
                ep.Remove(oldCall);
                if (eFpsIdx >= 0)
                {
                    eIl[eFpsIdx].Operand = fps;
                }
                else
                {
                    var retIns = eIl[eIl.Count - 1];
                    ep.InsertBefore(retIns, ep.Create(OpCodes.Ldc_I4, fps));
                    ep.InsertBefore(retIns, ep.Create(OpCodes.Call, setTargetFps));
                }
            }

            notes.Add("NOTE:fps:locked:" + fps);
            return true;
        }
        else
        {
            if (!plrLocked && !escLocked && eFpsIdx < 0) return false;
            if (plrLocked)
            {
                var pp = plrStart.Body.GetILProcessor();
                pp.Remove(pIl[pFpsIdx + 1]);
                pp.Remove(pIl[pFpsIdx]);
            }
            var ep = escSet.Body.GetILProcessor();
            if (escLocked)
            {
                var setRes3 = ResolveUnityMethod(mod, resolver, "UnityEngine.Screen", "SetResolution", 3);
                var oldCall = eIl[eRes4Idx];
                var fpsArg = eIl[eRes4Idx - 1];
                ep.InsertBefore(oldCall, ep.Create(OpCodes.Call, setRes3));
                ep.Remove(oldCall);
                ep.Remove(fpsArg);
            }
            eFpsIdx = FindCallPair(escSet, "set_targetFrameRate");
            if (eFpsIdx >= 0)
            {
                ep.Remove(eIl[eFpsIdx + 1]);
                ep.Remove(eIl[eFpsIdx]);
            }
            notes.Add("NOTE:fps:open");
            return true;
        }
    }

    private static void InspectAll(ModuleDefinition mod)
    {
        Console.WriteLine("song=" + InspectHold(mod, "MusicSelectControl", "time", 80));
        Console.WriteLine("mode10=" + InspectHold(mod, "JouneryModeSelect", "time", 10));
        Console.WriteLine("mode99=" + InspectHold(mod, "ModeSelect", "time", 99));
        Console.WriteLine("item=" + InspectHold(mod, "BuyItemManager", "time", 20));
        Console.WriteLine("play=" + InspectPlay(mod));
        Console.WriteLine("tutorial=" + InspectTutorial(mod));
        Console.WriteLine("gameover_return=" + InspectGameOverReturn(mod));
        Console.WriteLine("clear=" + InspectClear(mod));
        Console.WriteLine("offline=" + InspectOffline(mod));
        Console.WriteLine("masterlist=" + InspectMasterList(mod));
        Console.WriteLine("notes=" + InspectNotes(mod));
        Console.WriteLine("items=" + InspectItems(mod));
        Console.WriteLine("coins=" + InspectPlayerIntProp(mod, "Coins", 99999));
        Console.WriteLine("gems=" + InspectPlayerIntProp(mod, "Gems", 99999));
        Console.WriteLine("no_io=" + InspectNoIo(mod));
        Console.WriteLine("free_play=" + InspectFreePlay(mod));
        Console.WriteLine("fix_touch=" + InspectFixTouch(mod));
        Console.WriteLine("fps=" + InspectFps(mod));
        Console.WriteLine("vsync_off=" + InspectVsync(mod));
        Console.WriteLine("fps_display=" + InspectFpsDisplay(mod));
    }

    private static bool ApplyAll(ModuleDefinition mod, IAssemblyResolver resolver, Dictionary<string, string> choices)
    {
        bool changed = false;
        var notes = new List<string>();

        Func<string, bool> wantLock = k => choices.ContainsKey(k) && choices[k].StartsWith("1");
        Func<string, float> wantFloat = (k) =>
        {
            var parts = choices[k].Split('|');
            return float.Parse(parts[1], System.Globalization.CultureInfo.InvariantCulture);
        };
        Func<string, int> wantInt = (k) =>
        {
            var parts = choices[k].Split('|');
            return int.Parse(parts[1], System.Globalization.CultureInfo.InvariantCulture);
        };

        if (choices.ContainsKey("song")) changed |= ApplyHold(mod, "song", "MusicSelectControl", "time", wantLock("song"), wantLock("song") ? wantFloat("song") : 80f, notes);
        if (choices.ContainsKey("mode10")) changed |= ApplyHold(mod, "mode10", "JouneryModeSelect", "time", wantLock("mode10"), wantLock("mode10") ? wantFloat("mode10") : 10f, notes);
        if (choices.ContainsKey("mode99")) changed |= ApplyHold(mod, "mode99", "ModeSelect", "time", wantLock("mode99"), wantLock("mode99") ? wantFloat("mode99") : 99f, notes);
        if (choices.ContainsKey("item")) changed |= ApplyHold(mod, "item", "BuyItemManager", "time", wantLock("item"), wantLock("item") ? wantFloat("item") : 20f, notes);
        if (choices.ContainsKey("play")) changed |= ApplyPlay(mod, wantLock("play"), wantLock("play") ? wantInt("play") : 90, notes);
        if (choices.ContainsKey("tutorial")) changed |= ApplyTutorial(mod, wantLock("tutorial"), notes);
        if (choices.ContainsKey("clear")) changed |= ApplyClear(mod, wantLock("clear"), notes);
        if (choices.ContainsKey("offline")) changed |= ApplyOffline(mod, wantLock("offline"), notes);
        if (choices.ContainsKey("masterlist")) changed |= ApplyMasterList(mod, wantLock("masterlist"), notes);
        if (choices.ContainsKey("notes")) changed |= ApplyNotes(mod, resolver, wantLock("notes"), notes);
        if (choices.ContainsKey("items")) changed |= ApplyItems(mod, resolver, wantLock("items"), notes);
        if (choices.ContainsKey("coins")) changed |= ApplyPlayerIntProp(mod, "coins", "Coins", 99999, wantLock("coins"), notes);
        if (choices.ContainsKey("gems")) changed |= ApplyPlayerIntProp(mod, "gems", "Gems", 99999, wantLock("gems"), notes);
        if (choices.ContainsKey("no_io")) changed |= ApplyNoIo(mod, resolver, wantLock("no_io"), notes);
        if (choices.ContainsKey("free_play")) changed |= ApplyFreePlay(mod, wantLock("free_play"), notes);
        if (choices.ContainsKey("fix_touch")) changed |= ApplyFixTouch(mod, resolver, wantLock("fix_touch"), notes);
        if (choices.ContainsKey("fps")) changed |= ApplyFps(mod, resolver, wantLock("fps"), wantLock("fps") ? wantInt("fps") : 60, notes);
        if (choices.ContainsKey("vsync_off")) changed |= ApplyVsync(mod, resolver, wantLock("vsync_off"), notes);
        if (choices.ContainsKey("fps_display")) changed |= ApplyFpsDisplay(mod, wantLock("fps_display"), notes);
        if (choices.ContainsKey("gameover_return")) changed |= ApplyGameOverReturn(mod, resolver, wantLock("gameover_return"), notes);

        foreach (var n in notes) Console.WriteLine(n);
        return changed;
    }
}
