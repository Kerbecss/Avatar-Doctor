using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using NUnit.Framework;
using Teyocesu.AvatarDoctor.Editor.Discovery;
using Teyocesu.AvatarDoctor.Editor.Integrations.VRChat;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using VRC.SDK3.Avatars.Components;

namespace Teyocesu.AvatarDoctor.Editor.Tests
{
    internal sealed class AvatarDiscoveryServiceTests
    {
        private const string TemporaryAssetRoot =
            "Assets/__AvatarDoctorTestsTemp";
        private const string BaselineScenePath =
            TemporaryAssetRoot + "/Baseline.unity";

        private readonly List<Scene> previewScenes = new List<Scene>();
        private AvatarDiscoveryService service;

        [SetUp]
        public void SetUp()
        {
            CloseCurrentPrefabStage();
            ResetToEmptyScene();
            DeleteTemporaryAssets();
            SaveActiveSceneAsTestBaseline();
            service = new AvatarDiscoveryService();
        }

        [TearDown]
        public void TearDown()
        {
            CloseCurrentPrefabStage();
            foreach (Scene previewScene in previewScenes)
            {
                if (previewScene.IsValid() && previewScene.isLoaded)
                {
                    EditorSceneManager.ClosePreviewScene(previewScene);
                }
            }

            previewScenes.Clear();
            ResetToEmptyScene();
            DeleteTemporaryAssets();
        }

        [Test]
        public void Discover_WithNoDescriptors_ReturnsNone()
        {
            AvatarDiscoveryResult result = service.Discover();

            Assert.That(result.Candidates, Is.Empty);
            Assert.That(result.CountState, Is.EqualTo(AvatarDiscoveryState.None));
        }

        [Test]
        public void Discover_WithOneDescriptor_ReturnsSingleCandidate()
        {
            Scene scene = SceneManager.GetActiveScene();
            VRCAvatarDescriptor descriptor = CreateDescriptor(scene, "Avatar");

            AvatarDiscoveryResult result = service.Discover();

            Assert.That(result.Candidates, Has.Count.EqualTo(1));
            AvatarDiscoveryCandidate candidate = result.Candidates[0];
            Assert.That(candidate.DescriptorIdentity, Is.SameAs(descriptor));
            Assert.That(candidate.AvatarRoot, Is.SameAs(descriptor.gameObject));
            Assert.That(candidate.DisplayName, Is.EqualTo("Avatar"));
            Assert.That(candidate.DescriptorComponentOrdinal, Is.Zero);
            Assert.That(result.CountState, Is.EqualTo(AvatarDiscoveryState.Single));
        }

        [Test]
        public void Discover_WithMultipleDescriptors_ReturnsMultipleState()
        {
            Scene scene = SceneManager.GetActiveScene();
            CreateDescriptor(scene, "Avatar A");
            CreateDescriptor(scene, "Avatar B");

            AvatarDiscoveryResult result = service.Discover();

            Assert.That(result.Candidates, Has.Count.EqualTo(2));
            Assert.That(
                result.CountState,
                Is.EqualTo(AvatarDiscoveryState.Multiple));
        }

        [Test]
        public void Discover_IncludesInactiveRootAndInactiveDescendant()
        {
            Scene scene = SceneManager.GetActiveScene();
            VRCAvatarDescriptor inactiveRoot = CreateDescriptor(
                scene,
                "Inactive Root",
                null,
                false);
            GameObject parent = CreateGameObject(scene, "Parent", null, false);
            VRCAvatarDescriptor inactiveDescendant = CreateDescriptor(
                scene,
                "Inactive Child",
                parent.transform,
                false);

            AvatarDiscoveryResult result = service.Discover();

            Assert.That(
                result.Candidates.Select(candidate => candidate.DescriptorIdentity),
                Is.EquivalentTo(new UnityEngine.Object[]
                {
                    inactiveRoot,
                    inactiveDescendant,
                }));
        }

        [Test]
        public void Discover_AggregatesAllQualifyingLoadedScenes()
        {
            Scene firstScene = SceneManager.GetActiveScene();
            Scene secondScene = EditorSceneManager.NewScene(
                NewSceneSetup.EmptyScene,
                NewSceneMode.Additive);
            VRCAvatarDescriptor first = CreateDescriptor(firstScene, "First");
            VRCAvatarDescriptor second = CreateDescriptor(secondScene, "Second");

            AvatarDiscoveryResult result = service.Discover();

            Assert.That(
                result.Candidates.Select(candidate => candidate.DescriptorIdentity),
                Is.EquivalentTo(new UnityEngine.Object[] { first, second }));
        }

        [Test]
        public void Discover_DistinguishesDuplicateGameObjectNamesBySiblingIndex()
        {
            Scene scene = SceneManager.GetActiveScene();
            VRCAvatarDescriptor first = CreateDescriptor(scene, "Duplicate");
            VRCAvatarDescriptor second = CreateDescriptor(scene, "Duplicate");

            AvatarDiscoveryResult result = service.Discover();

            Assert.That(result.Candidates, Has.Count.EqualTo(2));
            Assert.That(
                result.Candidates[0].DescriptorIdentity,
                Is.SameAs(first));
            Assert.That(
                result.Candidates[1].DescriptorIdentity,
                Is.SameAs(second));
            Assert.That(
                result.Candidates[0].HierarchyDisplayPath,
                Is.Not.EqualTo(result.Candidates[1].HierarchyDisplayPath));
            Assert.That(result.Candidates[0].HierarchyDisplayPath, Does.Contain("[0]"));
            Assert.That(result.Candidates[1].HierarchyDisplayPath, Does.Contain("[1]"));
        }

        [Test]
        public void Discover_AssignsAndOrdersSameRootDescriptorOrdinals()
        {
            Scene scene = SceneManager.GetActiveScene();
            GameObject avatarRoot = CreateGameObject(scene, "Same Root");
            VRCAvatarDescriptor first =
                avatarRoot.AddComponent<VRCAvatarDescriptor>();
            VRCAvatarDescriptor second =
                avatarRoot.AddComponent<VRCAvatarDescriptor>();

            AvatarDiscoveryResult result = service.Discover();

            Assert.That(result.Candidates, Has.Count.EqualTo(2));
            Assert.That(
                result.Candidates.Select(
                    candidate => candidate.DescriptorComponentOrdinal),
                Is.EqualTo(new[] { 0, 1 }));
            Assert.That(result.Candidates[0].DescriptorIdentity, Is.SameAs(first));
            Assert.That(result.Candidates[1].DescriptorIdentity, Is.SameAs(second));
        }

        [Test]
        public void Discover_SortsSavedPathsBeforeUnsavedScene()
        {
            CreateSavedScene(
                TemporaryAssetRoot + "/Z.unity",
                "Saved Z");
            CreateSavedScene(
                TemporaryAssetRoot + "/A.unity",
                "Saved A");
            Scene unsavedScene = EditorSceneManager.NewScene(
                NewSceneSetup.EmptyScene,
                NewSceneMode.Additive);
            CreateDescriptor(unsavedScene, "Unsaved");

            AvatarDiscoveryResult result = service.Discover();

            Assert.That(
                result.Candidates.Select(candidate => candidate.DisplayName),
                Is.EqualTo(new[] { "Saved A", "Saved Z", "Unsaved" }));
        }

        [Test]
        public void Discover_DuplicateSceneNamesUseDistinctSavedPaths()
        {
            EnsureAssetFolder(TemporaryAssetRoot + "/A");
            EnsureAssetFolder(TemporaryAssetRoot + "/B");
            Scene first = CreateSavedScene(
                TemporaryAssetRoot + "/A/Duplicate.unity",
                "First");
            Scene second = CreateSavedScene(
                TemporaryAssetRoot + "/B/Duplicate.unity",
                "Second");
            Assert.That(first.name, Is.EqualTo(second.name));

            AvatarDiscoveryResult result = service.Discover();

            Assert.That(result.Candidates, Has.Count.EqualTo(2));
            Assert.That(
                result.Candidates[0].SceneIdentity,
                Is.EqualTo(TemporaryAssetRoot + "/A/Duplicate.unity"));
            Assert.That(
                result.Candidates[1].SceneIdentity,
                Is.EqualTo(TemporaryAssetRoot + "/B/Duplicate.unity"));
        }

        [Test]
        public void Discover_RepeatedCallsReturnSameCandidateOrder()
        {
            Scene scene = SceneManager.GetActiveScene();
            GameObject first = CreateGameObject(scene, "Duplicate");
            first.AddComponent<VRCAvatarDescriptor>();
            first.AddComponent<VRCAvatarDescriptor>();
            CreateDescriptor(scene, "Duplicate");

            int[] firstOrder = service.Discover().Candidates
                .Select(candidate => candidate.DescriptorInstanceId)
                .ToArray();
            int[] secondOrder = service.Discover().Candidates
                .Select(candidate => candidate.DescriptorInstanceId)
                .ToArray();

            Assert.That(secondOrder, Is.EqualTo(firstOrder));
        }

        [Test]
        public void IsSceneEligible_RequiresValidLoadedNonPreviewScene()
        {
            Scene regularScene = SceneManager.GetActiveScene();
            Scene previewScene = EditorSceneManager.NewPreviewScene();
            previewScenes.Add(previewScene);

            Assert.That(
                AvatarDiscoveryService.IsSceneEligible(default),
                Is.False);
            Assert.That(
                AvatarDiscoveryService.IsSceneEligible(regularScene),
                Is.True);
            Assert.That(
                AvatarDiscoveryService.IsSceneEligible(previewScene),
                Is.False);
        }

        [Test]
        public void Discover_ExcludesPreviewSceneDescriptors()
        {
            Scene regularScene = SceneManager.GetActiveScene();
            VRCAvatarDescriptor regular = CreateDescriptor(
                regularScene,
                "Regular");
            Scene previewScene = EditorSceneManager.NewPreviewScene();
            previewScenes.Add(previewScene);
            CreateDescriptor(previewScene, "Preview");

            AvatarDiscoveryResult result = service.Discover();

            Assert.That(result.Candidates, Has.Count.EqualTo(1));
            Assert.That(result.Candidates[0].DescriptorIdentity, Is.SameAs(regular));
        }

        [Test]
        public void Discover_ExcludesUnloadedSceneAsset()
        {
            Scene scene = CreateSavedScene(
                TemporaryAssetRoot + "/Unloaded.unity",
                "Unloaded Avatar");
            Assert.That(scene.isDirty, Is.False);
            Assert.That(EditorSceneManager.CloseScene(scene, true), Is.True);

            AvatarDiscoveryResult result = service.Discover();

            Assert.That(result.Candidates, Is.Empty);
        }

        [Test]
        public void Discover_ExcludesDescriptorInPrefabStage()
        {
            const string prefabPath =
                TemporaryAssetRoot + "/PrefabStageAvatar.prefab";
            CreatePrefabAssetWithDescriptor(prefabPath);

            PrefabStage stage = PrefabStageUtility.OpenPrefab(prefabPath);

            Assert.That(stage, Is.Not.Null);
            Assert.That(EditorSceneManager.IsPreviewScene(stage.scene), Is.True);
            Assert.That(service.Discover().Candidates, Is.Empty);
            StageUtility.GoBackToPreviousStage();
        }

        [Test]
        public void Discover_IncludesPrefabInstanceInRegularScene()
        {
            const string prefabPath =
                TemporaryAssetRoot + "/RegularSceneAvatar.prefab";
            GameObject prefab = CreatePrefabAssetWithDescriptor(prefabPath);
            Scene scene = SceneManager.GetActiveScene();
            GameObject instance = PrefabUtility.InstantiatePrefab(
                prefab,
                scene) as GameObject;

            AvatarDiscoveryResult result = service.Discover();

            Assert.That(instance, Is.Not.Null);
            Assert.That(result.Candidates, Has.Count.EqualTo(1));
            Assert.That(result.Candidates[0].AvatarRoot, Is.SameAs(instance));
        }

        [Test]
        public void Discover_DoesNotPublishDestroyedDescriptorReference()
        {
            Scene scene = SceneManager.GetActiveScene();
            VRCAvatarDescriptor descriptor = CreateDescriptor(scene, "Destroyed");
            AvatarDiscoveryCandidate staleCandidate =
                service.Discover().Candidates[0];

            UnityEngine.Object.DestroyImmediate(descriptor);

            Assert.That(
                VRChatAvatarDescriptorBoundary.IsCandidateLive(staleCandidate),
                Is.False);
            Assert.That(service.Discover().Candidates, Is.Empty);
        }

        [Test]
        public void Discover_DoesNotMutateSceneObjectsComponentsAssetsOrUndo()
        {
            const string scenePath =
                TemporaryAssetRoot + "/ReadOnlyScene.unity";
            const string prefabPath =
                TemporaryAssetRoot + "/ReadOnlyAsset.prefab";
            Scene scene = SceneManager.GetActiveScene();
            VRCAvatarDescriptor descriptor = CreateDescriptor(scene, "Read Only");
            CreatePrefabAssetWithDescriptor(prefabPath);
            EnsureAssetFolder(TemporaryAssetRoot);
            Assert.That(EditorSceneManager.SaveScene(scene, scenePath), Is.True);
            Assert.That(scene.isDirty, Is.False);

            GameObject avatarRoot = descriptor.gameObject;
            string nameBefore = avatarRoot.name;
            bool activeSelfBefore = avatarRoot.activeSelf;
            Transform parentBefore = avatarRoot.transform.parent;
            int siblingIndexBefore = avatarRoot.transform.GetSiblingIndex();
            UnityEngine.Object descriptorIdentityBefore = descriptor;
            string descriptorBefore = EditorJsonUtility.ToJson(descriptor, true);
            int[] objectIdsBefore = GetSceneObjectInstanceIds(scene);
            int[] componentIdsBefore = GetSceneComponentInstanceIds(scene);
            byte[] sceneBytesBefore = File.ReadAllBytes(scenePath);
            Hash128 sceneHashBefore = AssetDatabase.GetAssetDependencyHash(scenePath);
            Hash128 prefabHashBefore = AssetDatabase.GetAssetDependencyHash(prefabPath);
            string[] assetsBefore = AssetDatabase.FindAssets(
                string.Empty,
                new[] { TemporaryAssetRoot });
            int undoGroupBefore = Undo.GetCurrentGroup();
            bool dirtyBefore = scene.isDirty;

            AvatarDiscoveryResult result = service.Discover();

            Assert.That(result.Candidates, Has.Count.EqualTo(1));
            Assert.That(
                result.Candidates[0].DescriptorIdentity,
                Is.SameAs(descriptorIdentityBefore));
            Assert.That(result.Candidates[0].AvatarRoot, Is.SameAs(avatarRoot));
            Assert.That(scene.isDirty, Is.EqualTo(dirtyBefore));
            Assert.That(scene.isDirty, Is.False);
            Assert.That(avatarRoot.name, Is.EqualTo(nameBefore));
            Assert.That(avatarRoot.activeSelf, Is.EqualTo(activeSelfBefore));
            Assert.That(avatarRoot.transform.parent, Is.SameAs(parentBefore));
            Assert.That(
                avatarRoot.transform.GetSiblingIndex(),
                Is.EqualTo(siblingIndexBefore));
            Assert.That(descriptor, Is.SameAs(descriptorIdentityBefore));
            Assert.That(
                EditorJsonUtility.ToJson(descriptor, true),
                Is.EqualTo(descriptorBefore));
            Assert.That(
                GetSceneObjectInstanceIds(scene),
                Is.EqualTo(objectIdsBefore));
            Assert.That(
                GetSceneComponentInstanceIds(scene),
                Is.EqualTo(componentIdsBefore));
            Assert.That(File.ReadAllBytes(scenePath), Is.EqualTo(sceneBytesBefore));
            Assert.That(
                AssetDatabase.GetAssetDependencyHash(scenePath),
                Is.EqualTo(sceneHashBefore));
            Assert.That(
                AssetDatabase.GetAssetDependencyHash(prefabPath),
                Is.EqualTo(prefabHashBefore));
            Assert.That(
                AssetDatabase.FindAssets(
                    string.Empty,
                    new[] { TemporaryAssetRoot }),
                Is.EqualTo(assetsBefore));
            Assert.That(Undo.GetCurrentGroup(), Is.EqualTo(undoGroupBefore));
        }

        private static VRCAvatarDescriptor CreateDescriptor(
            Scene scene,
            string name,
            Transform parent = null,
            bool active = true)
        {
            return CreateGameObject(scene, name, parent, active)
                .AddComponent<VRCAvatarDescriptor>();
        }

        private static GameObject CreateGameObject(
            Scene scene,
            string name,
            Transform parent = null,
            bool active = true)
        {
            GameObject gameObject = new GameObject(name);
            SceneManager.MoveGameObjectToScene(gameObject, scene);
            if (parent != null)
            {
                gameObject.transform.SetParent(parent, false);
            }

            gameObject.SetActive(active);
            return gameObject;
        }

        private static Scene CreateSavedScene(
            string scenePath,
            string avatarName)
        {
            EnsureAssetFolder(
                scenePath.Substring(0, scenePath.LastIndexOf('/')));
            Scene scene = EditorSceneManager.NewScene(
                NewSceneSetup.EmptyScene,
                NewSceneMode.Additive);
            CreateDescriptor(scene, avatarName);
            Assert.That(EditorSceneManager.SaveScene(scene, scenePath), Is.True);
            Assert.That(scene.isDirty, Is.False);
            return scene;
        }

        private static GameObject CreatePrefabAssetWithDescriptor(
            string prefabPath)
        {
            EnsureAssetFolder(
                prefabPath.Substring(0, prefabPath.LastIndexOf('/')));
            GameObject source = new GameObject("Prefab Avatar");
            source.AddComponent<VRCAvatarDescriptor>();
            GameObject prefab = PrefabUtility.SaveAsPrefabAsset(
                source,
                prefabPath);
            UnityEngine.Object.DestroyImmediate(source);
            Assert.That(prefab, Is.Not.Null);
            return prefab;
        }

        private static void EnsureAssetFolder(string folderPath)
        {
            string[] segments = folderPath.Split('/');
            string current = segments[0];
            for (int index = 1; index < segments.Length; index++)
            {
                string next = current + "/" + segments[index];
                if (!AssetDatabase.IsValidFolder(next))
                {
                    AssetDatabase.CreateFolder(current, segments[index]);
                }

                current = next;
            }
        }

        private static int[] GetSceneObjectInstanceIds(Scene scene)
        {
            List<int> instanceIds = new List<int>();
            foreach (GameObject root in scene.GetRootGameObjects())
            {
                instanceIds.AddRange(root
                    .GetComponentsInChildren<Transform>(true)
                    .Select(transform => transform.gameObject.GetInstanceID()));
            }

            instanceIds.Sort();
            return instanceIds.ToArray();
        }

        private static int[] GetSceneComponentInstanceIds(Scene scene)
        {
            List<int> instanceIds = new List<int>();
            foreach (GameObject root in scene.GetRootGameObjects())
            {
                foreach (Transform transform in
                    root.GetComponentsInChildren<Transform>(true))
                {
                    instanceIds.AddRange(transform.gameObject
                        .GetComponents<Component>()
                        .Where(component => component != null)
                        .Select(component => component.GetInstanceID()));
                }
            }

            instanceIds.Sort();
            return instanceIds.ToArray();
        }

        private static void CloseCurrentPrefabStage()
        {
            if (PrefabStageUtility.GetCurrentPrefabStage() != null)
            {
                StageUtility.GoBackToPreviousStage();
            }
        }

        private static void ResetToEmptyScene()
        {
            EditorSceneManager.NewScene(
                NewSceneSetup.EmptyScene,
                NewSceneMode.Single);
        }

        private static void SaveActiveSceneAsTestBaseline()
        {
            EnsureAssetFolder(TemporaryAssetRoot);
            Scene scene = SceneManager.GetActiveScene();
            Assert.That(
                EditorSceneManager.SaveScene(scene, BaselineScenePath),
                Is.True);
            Assert.That(scene.isDirty, Is.False);
        }

        private static void DeleteTemporaryAssets()
        {
            if (AssetDatabase.IsValidFolder(TemporaryAssetRoot))
            {
                AssetDatabase.DeleteAsset(TemporaryAssetRoot);
                AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            }
        }
    }
}
