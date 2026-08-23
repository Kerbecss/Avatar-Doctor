using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using Teyocesu.AvatarDoctor.Editor.Discovery;
using Teyocesu.AvatarDoctor.Editor.Selection;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using VRC.SDK3.Avatars.Components;
using UnityObject = UnityEngine.Object;

namespace Teyocesu.AvatarDoctor.Editor.Tests
{
    internal sealed class AvatarSelectionIntegrationTests
    {
        private const string TemporaryAssetRoot =
            "Assets/__AvatarDoctorSelectionTestsTemp";
        private const string BaselineScenePath =
            TemporaryAssetRoot + "/Baseline.unity";

        private AvatarDiscoveryService discoveryService;
        private AvatarSelectionModel selectionModel;
        private UnityObject previousEditorSelection;

        [SetUp]
        public void SetUp()
        {
            previousEditorSelection = UnityEditor.Selection.activeObject;
            UnityEditor.Selection.activeObject = null;
            ResetToEmptyScene();
            DeleteTemporaryAssets();
            SaveActiveSceneAsBaseline();
            discoveryService = new AvatarDiscoveryService();
            selectionModel = new AvatarSelectionModel();
        }

        [TearDown]
        public void TearDown()
        {
            UnityEditor.Selection.activeObject = null;
            ResetToEmptyScene();
            DeleteTemporaryAssets();
            if (previousEditorSelection != null)
            {
                UnityEditor.Selection.activeObject = previousEditorSelection;
            }
        }

        [Test]
        public void Refresh_RebindsManualSelectionToNewDiscoveryCandidate()
        {
            Scene scene = SceneManager.GetActiveScene();
            VRCAvatarDescriptor first = CreateDescriptor(scene, "First");
            VRCAvatarDescriptor second = CreateDescriptor(scene, "Second");
            AvatarDiscoveryResult initialResult = discoveryService.Discover();
            AvatarDiscoveryCandidate initialFirst = CandidateFor(
                initialResult,
                first);
            selectionModel.ApplyDiscoveryResult(initialResult, null);
            Assert.That(selectionModel.TrySelectManual(initialFirst), Is.True);

            AvatarDiscoveryResult refreshedResult = discoveryService.Discover();
            AvatarDiscoveryCandidate refreshedFirst = CandidateFor(
                refreshedResult,
                first);
            AvatarSelection selection = selectionModel.ApplyDiscoveryResult(
                refreshedResult,
                second.gameObject);

            Assert.That(selection.Candidate, Is.SameAs(refreshedFirst));
            Assert.That(selection.Candidate, Is.Not.SameAs(initialFirst));
            Assert.That(selection.Origin, Is.EqualTo(AvatarSelectionOrigin.Manual));
        }

        [Test]
        public void Refresh_DestroyedManualCandidateSelectsSoleLiveCandidate()
        {
            Scene scene = SceneManager.GetActiveScene();
            VRCAvatarDescriptor first = CreateDescriptor(scene, "First");
            VRCAvatarDescriptor second = CreateDescriptor(scene, "Second");
            AvatarDiscoveryResult initialResult = discoveryService.Discover();
            selectionModel.ApplyDiscoveryResult(initialResult, null);
            Assert.That(
                selectionModel.TrySelectManual(CandidateFor(initialResult, first)),
                Is.True);

            UnityObject.DestroyImmediate(first);
            AvatarDiscoveryResult refreshedResult = discoveryService.Discover();
            AvatarSelection selection = selectionModel.ApplyDiscoveryResult(
                refreshedResult,
                null);

            Assert.That(selection.Candidate.DescriptorIdentity, Is.SameAs(second));
            Assert.That(
                selection.Origin,
                Is.EqualTo(AvatarSelectionOrigin.AutomaticSingle));
        }

        [Test]
        public void Refresh_UnloadedManualCandidateSelectsSoleLoadedCandidate()
        {
            Scene mainScene = SceneManager.GetActiveScene();
            VRCAvatarDescriptor remaining = CreateDescriptor(mainScene, "Remaining");
            Scene additiveScene = EditorSceneManager.NewScene(
                NewSceneSetup.EmptyScene,
                NewSceneMode.Additive);
            VRCAvatarDescriptor unloaded = CreateDescriptor(
                additiveScene,
                "Unloaded");
            AvatarDiscoveryResult initialResult = discoveryService.Discover();
            selectionModel.ApplyDiscoveryResult(initialResult, null);
            Assert.That(
                selectionModel.TrySelectManual(
                    CandidateFor(initialResult, unloaded)),
                Is.True);

            Assert.That(EditorSceneManager.CloseScene(additiveScene, true), Is.True);
            AvatarDiscoveryResult refreshedResult = discoveryService.Discover();
            AvatarSelection selection = selectionModel.ApplyDiscoveryResult(
                refreshedResult,
                null);

            Assert.That(selection.Candidate.DescriptorIdentity, Is.SameAs(remaining));
            Assert.That(
                selection.Origin,
                Is.EqualTo(AvatarSelectionOrigin.AutomaticSingle));
        }

        [Test]
        public void TrySelectManual_DestroyedCandidateIsRejectedImmediately()
        {
            Scene scene = SceneManager.GetActiveScene();
            VRCAvatarDescriptor stale = CreateDescriptor(scene, "Stale");
            VRCAvatarDescriptor remaining = CreateDescriptor(scene, "Remaining");
            AvatarDiscoveryResult result = discoveryService.Discover();
            AvatarDiscoveryCandidate staleCandidate = CandidateFor(result, stale);
            selectionModel.ApplyDiscoveryResult(result, null);

            UnityObject.DestroyImmediate(stale);
            bool selected = selectionModel.TrySelectManual(staleCandidate);

            Assert.That(selected, Is.False);
            Assert.That(selectionModel.DiscoveryResult.Candidates, Has.Count.EqualTo(1));
            Assert.That(
                selectionModel.CurrentSelection.Candidate.DescriptorIdentity,
                Is.SameAs(remaining));
            Assert.That(
                selectionModel.CurrentSelection.Origin,
                Is.EqualTo(AvatarSelectionOrigin.AutomaticSingle));
        }

        [Test]
        public void EditorSelection_ComponentUsesNearestNestedAvatarRoot()
        {
            Scene scene = SceneManager.GetActiveScene();
            VRCAvatarDescriptor outer = CreateDescriptor(scene, "Outer");
            VRCAvatarDescriptor inner = CreateDescriptor(
                scene,
                "Inner",
                outer.transform);
            GameObject descendant = CreateGameObject(
                scene,
                "Descendant",
                inner.transform);
            BoxCollider selectedComponent = descendant.AddComponent<BoxCollider>();
            AvatarDiscoveryResult result = discoveryService.Discover();
            selectionModel.ApplyDiscoveryResult(result, null);

            AvatarSelection selection = selectionModel.ApplyEditorSelection(
                selectedComponent);

            Assert.That(selection.Candidate.DescriptorIdentity, Is.SameAs(inner));
            Assert.That(
                selection.Origin,
                Is.EqualTo(AvatarSelectionOrigin.AutomaticEditorSelection));
        }

        [Test]
        public void EditorSelection_SameRootDescriptorsRemainUnresolved()
        {
            Scene scene = SceneManager.GetActiveScene();
            GameObject sharedRoot = CreateGameObject(scene, "Shared Root");
            sharedRoot.AddComponent<VRCAvatarDescriptor>();
            sharedRoot.AddComponent<VRCAvatarDescriptor>();

            AvatarSelection selection = selectionModel.ApplyDiscoveryResult(
                discoveryService.Discover(),
                sharedRoot);

            Assert.That(
                selection.State,
                Is.EqualTo(AvatarSelectionState.Unresolved));
            Assert.That(selection.Candidate, Is.Null);
        }

        [Test]
        public void SelectionOperations_DoNotMutateEditorSceneOrSelection()
        {
            Scene scene = SceneManager.GetActiveScene();
            VRCAvatarDescriptor first = CreateDescriptor(scene, "First");
            VRCAvatarDescriptor second = CreateDescriptor(scene, "Second");
            GameObject descendant = CreateGameObject(
                scene,
                "Descendant",
                first.transform);
            GameObject editorSelection = CreateGameObject(scene, "Editor Selection");
            UnityEditor.Selection.activeObject = editorSelection;
            AvatarDiscoveryResult result = discoveryService.Discover();
            AvatarDiscoveryCandidate firstCandidate = CandidateFor(result, first);
            string firstBefore = EditorJsonUtility.ToJson(first, true);
            string secondBefore = EditorJsonUtility.ToJson(second, true);
            int[] objectIdsBefore = GetSceneObjectInstanceIds(scene);
            int[] componentIdsBefore = GetSceneComponentInstanceIds(scene);
            bool dirtyBefore = scene.isDirty;
            int undoGroupBefore = Undo.GetCurrentGroup();
            Transform parentBefore = descendant.transform.parent;
            int siblingIndexBefore = descendant.transform.GetSiblingIndex();
            bool activeBefore = descendant.activeSelf;

            selectionModel.ApplyDiscoveryResult(result, descendant.transform);
            Assert.That(selectionModel.TrySelectManual(firstCandidate), Is.True);
            selectionModel.ApplyEditorSelection(second.gameObject);

            Assert.That(scene.isDirty, Is.EqualTo(dirtyBefore));
            Assert.That(EditorJsonUtility.ToJson(first, true), Is.EqualTo(firstBefore));
            Assert.That(EditorJsonUtility.ToJson(second, true), Is.EqualTo(secondBefore));
            Assert.That(GetSceneObjectInstanceIds(scene), Is.EqualTo(objectIdsBefore));
            Assert.That(
                GetSceneComponentInstanceIds(scene),
                Is.EqualTo(componentIdsBefore));
            Assert.That(Undo.GetCurrentGroup(), Is.EqualTo(undoGroupBefore));
            Assert.That(descendant.transform.parent, Is.SameAs(parentBefore));
            Assert.That(
                descendant.transform.GetSiblingIndex(),
                Is.EqualTo(siblingIndexBefore));
            Assert.That(descendant.activeSelf, Is.EqualTo(activeBefore));
            Assert.That(
                UnityEditor.Selection.activeObject,
                Is.SameAs(editorSelection));
        }

        private static AvatarDiscoveryCandidate CandidateFor(
            AvatarDiscoveryResult result,
            VRCAvatarDescriptor descriptor)
        {
            return result.Candidates.Single(candidate =>
                candidate.DescriptorIdentity == descriptor);
        }

        private static VRCAvatarDescriptor CreateDescriptor(
            Scene scene,
            string name,
            Transform parent = null)
        {
            return CreateGameObject(scene, name, parent)
                .AddComponent<VRCAvatarDescriptor>();
        }

        private static GameObject CreateGameObject(
            Scene scene,
            string name,
            Transform parent = null)
        {
            GameObject gameObject = new GameObject(name);
            SceneManager.MoveGameObjectToScene(gameObject, scene);
            if (parent != null)
            {
                gameObject.transform.SetParent(parent, false);
            }

            return gameObject;
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

        private static void ResetToEmptyScene()
        {
            EditorSceneManager.NewScene(
                NewSceneSetup.EmptyScene,
                NewSceneMode.Single);
        }

        private static void SaveActiveSceneAsBaseline()
        {
            EnsureAssetFolder(TemporaryAssetRoot);
            Scene scene = SceneManager.GetActiveScene();
            Assert.That(
                EditorSceneManager.SaveScene(scene, BaselineScenePath),
                Is.True);
            Assert.That(scene.isDirty, Is.False);
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
