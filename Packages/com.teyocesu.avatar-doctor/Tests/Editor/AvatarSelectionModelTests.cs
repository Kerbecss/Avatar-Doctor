using System;
using System.Collections.Generic;
using NUnit.Framework;
using Teyocesu.AvatarDoctor.Editor.Discovery;
using Teyocesu.AvatarDoctor.Editor.Selection;
using UnityEngine;
using UnityObject = UnityEngine.Object;

namespace Teyocesu.AvatarDoctor.Editor.Tests
{
    internal sealed class AvatarSelectionModelTests
    {
        private readonly List<GameObject> objects = new List<GameObject>();
        private readonly List<UnityObject> invalidIdentities =
            new List<UnityObject>();
        private AvatarSelectionModel model;

        [SetUp]
        public void SetUp()
        {
            model = new AvatarSelectionModel(IsCandidateLive);
        }

        [TearDown]
        public void TearDown()
        {
            foreach (GameObject gameObject in objects)
            {
                if (gameObject != null)
                {
                    UnityObject.DestroyImmediate(gameObject);
                }
            }

            objects.Clear();
            invalidIdentities.Clear();
        }

        [Test]
        public void ApplyDiscoveryResult_WithNoCandidates_ClearsManualSelection()
        {
            AvatarDiscoveryCandidate first = CreateCandidate("First");
            AvatarDiscoveryCandidate second = CreateCandidate("Second");
            model.ApplyDiscoveryResult(CreateResult(first, second), null);
            Assert.That(model.TrySelectManual(first), Is.True);

            AvatarSelection selection = model.ApplyDiscoveryResult(
                CreateResult(),
                second.AvatarRoot);

            Assert.That(selection.State, Is.EqualTo(AvatarSelectionState.Empty));
            Assert.That(selection.Candidate, Is.Null);
            Assert.That(selection.Origin, Is.Null);
        }

        [Test]
        public void ApplyDiscoveryResult_WithSoleCandidate_UsesAutomaticSingle()
        {
            AvatarDiscoveryCandidate first = CreateCandidate("First");
            AvatarDiscoveryCandidate second = CreateCandidate("Second");
            model.ApplyDiscoveryResult(CreateResult(first, second), null);
            Assert.That(model.TrySelectManual(first), Is.True);
            AvatarDiscoveryCandidate refreshedFirst = CopyCandidate(first);

            AvatarSelection selection = model.ApplyDiscoveryResult(
                CreateResult(refreshedFirst),
                second.AvatarRoot);

            Assert.That(selection.Candidate, Is.SameAs(refreshedFirst));
            Assert.That(
                selection.Origin,
                Is.EqualTo(AvatarSelectionOrigin.AutomaticSingle));
        }

        [Test]
        public void ApplyDiscoveryResult_WithMultipleAndNoSafeChoice_IsUnresolved()
        {
            AvatarDiscoveryCandidate first = CreateCandidate("First");
            AvatarDiscoveryCandidate second = CreateCandidate("Second");

            AvatarSelection selection = model.ApplyDiscoveryResult(
                CreateResult(first, second),
                null);

            Assert.That(
                selection.State,
                Is.EqualTo(AvatarSelectionState.Unresolved));
            Assert.That(selection.Candidate, Is.Null);
            Assert.That(selection.Origin, Is.Null);
        }

        [Test]
        public void Refresh_RebindsAndPreservesManualSelectionBeforeEditorMapping()
        {
            AvatarDiscoveryCandidate first = CreateCandidate("First");
            AvatarDiscoveryCandidate second = CreateCandidate("Second");
            model.ApplyDiscoveryResult(CreateResult(first, second), null);
            Assert.That(model.TrySelectManual(first), Is.True);
            AvatarDiscoveryCandidate refreshedFirst = CopyCandidate(first);
            AvatarDiscoveryCandidate refreshedSecond = CopyCandidate(second);

            AvatarSelection selection = model.ApplyDiscoveryResult(
                CreateResult(refreshedFirst, refreshedSecond),
                second.AvatarRoot);

            Assert.That(selection.Candidate, Is.SameAs(refreshedFirst));
            Assert.That(selection.Candidate, Is.Not.SameAs(first));
            Assert.That(selection.Origin, Is.EqualTo(AvatarSelectionOrigin.Manual));
        }

        [Test]
        public void Refresh_RebindsAndPreservesAutomaticSelectionBeforeEditorMapping()
        {
            AvatarDiscoveryCandidate first = CreateCandidate("First");
            AvatarDiscoveryCandidate second = CreateCandidate("Second");
            AvatarSelection initial = model.ApplyDiscoveryResult(
                CreateResult(first, second),
                first.AvatarRoot);
            Assert.That(
                initial.Origin,
                Is.EqualTo(AvatarSelectionOrigin.AutomaticEditorSelection));
            AvatarDiscoveryCandidate refreshedFirst = CopyCandidate(first);
            AvatarDiscoveryCandidate refreshedSecond = CopyCandidate(second);

            AvatarSelection selection = model.ApplyDiscoveryResult(
                CreateResult(refreshedFirst, refreshedSecond),
                second.AvatarRoot);

            Assert.That(selection.Candidate, Is.SameAs(refreshedFirst));
            Assert.That(selection.Candidate, Is.Not.SameAs(first));
            Assert.That(
                selection.Origin,
                Is.EqualTo(AvatarSelectionOrigin.AutomaticEditorSelection));
        }

        [Test]
        public void Refresh_PreservesAutomaticSingleWhenMultipleCandidatesAppear()
        {
            AvatarDiscoveryCandidate first = CreateCandidate("First");
            AvatarSelection initial = model.ApplyDiscoveryResult(
                CreateResult(first),
                null);
            Assert.That(
                initial.Origin,
                Is.EqualTo(AvatarSelectionOrigin.AutomaticSingle));
            AvatarDiscoveryCandidate refreshedFirst = CopyCandidate(first);
            AvatarDiscoveryCandidate second = CreateCandidate("Second");

            AvatarSelection selection = model.ApplyDiscoveryResult(
                CreateResult(refreshedFirst, second),
                second.AvatarRoot);

            Assert.That(selection.Candidate, Is.SameAs(refreshedFirst));
            Assert.That(selection.Candidate, Is.Not.SameAs(first));
            Assert.That(
                selection.Origin,
                Is.EqualTo(AvatarSelectionOrigin.AutomaticSingle));
        }

        [Test]
        public void EditorSelection_SafeMappingReplacesAutomaticSelection()
        {
            AvatarDiscoveryCandidate first = CreateCandidate("First");
            AvatarDiscoveryCandidate second = CreateCandidate("Second");
            model.ApplyDiscoveryResult(
                CreateResult(first, second),
                first.AvatarRoot);

            AvatarSelection selection = model.ApplyEditorSelection(
                second.AvatarRoot);

            Assert.That(selection.Candidate, Is.SameAs(second));
            Assert.That(
                selection.Origin,
                Is.EqualTo(AvatarSelectionOrigin.AutomaticEditorSelection));
        }

        [Test]
        public void EditorSelection_ValidManualSelectionIsNeverOverridden()
        {
            AvatarDiscoveryCandidate first = CreateCandidate("First");
            AvatarDiscoveryCandidate second = CreateCandidate("Second");
            model.ApplyDiscoveryResult(CreateResult(first, second), null);
            Assert.That(model.TrySelectManual(first), Is.True);

            AvatarSelection selection = model.ApplyEditorSelection(
                second.AvatarRoot);

            Assert.That(selection.Candidate, Is.SameAs(first));
            Assert.That(selection.Origin, Is.EqualTo(AvatarSelectionOrigin.Manual));
        }

        [Test]
        public void EditorSelection_MapsRootDescendantAndComponent()
        {
            AvatarDiscoveryCandidate first = CreateCandidate("First");
            AvatarDiscoveryCandidate second = CreateCandidate("Second");
            GameObject descendant = CreateGameObject(
                "Descendant",
                first.AvatarRoot.transform);
            BoxCollider component = descendant.AddComponent<BoxCollider>();
            model.ApplyDiscoveryResult(CreateResult(first, second), null);

            Assert.That(
                model.ApplyEditorSelection(first.AvatarRoot).Candidate,
                Is.SameAs(first));
            Assert.That(
                model.ApplyEditorSelection(descendant).Candidate,
                Is.SameAs(first));
            Assert.That(
                model.ApplyEditorSelection(component).Candidate,
                Is.SameAs(first));
        }

        [Test]
        public void EditorSelection_UsesNearestNestedAvatarRoot()
        {
            AvatarDiscoveryCandidate outer = CreateCandidate("Outer");
            GameObject innerRoot = CreateGameObject(
                "Inner",
                outer.AvatarRoot.transform);
            AvatarDiscoveryCandidate inner = CreateCandidate(
                "Inner",
                innerRoot,
                innerRoot);
            GameObject descendant = CreateGameObject(
                "Descendant",
                innerRoot.transform);
            model.ApplyDiscoveryResult(CreateResult(outer, inner), null);

            AvatarSelection selection = model.ApplyEditorSelection(descendant);

            Assert.That(selection.Candidate, Is.SameAs(inner));
            Assert.That(
                selection.Origin,
                Is.EqualTo(AvatarSelectionOrigin.AutomaticEditorSelection));
        }

        [Test]
        public void EditorSelection_WithSameRootDescriptors_IsAmbiguous()
        {
            GameObject sharedRoot = CreateGameObject("Shared Root");
            GameObject firstIdentity = CreateGameObject("First Identity");
            GameObject secondIdentity = CreateGameObject("Second Identity");
            AvatarDiscoveryCandidate first = CreateCandidate(
                "Shared Root",
                sharedRoot,
                firstIdentity,
                0);
            AvatarDiscoveryCandidate second = CreateCandidate(
                "Shared Root",
                sharedRoot,
                secondIdentity,
                1);

            AvatarSelection selection = model.ApplyDiscoveryResult(
                CreateResult(first, second),
                sharedRoot);

            Assert.That(
                selection.State,
                Is.EqualTo(AvatarSelectionState.Unresolved));
            Assert.That(selection.Candidate, Is.Null);
        }

        [Test]
        public void EditorSelection_OutsideAvatarsPreservesValidAutomaticSelection()
        {
            AvatarDiscoveryCandidate first = CreateCandidate("First");
            AvatarDiscoveryCandidate second = CreateCandidate("Second");
            GameObject outside = CreateGameObject("Outside");
            model.ApplyDiscoveryResult(
                CreateResult(first, second),
                first.AvatarRoot);

            AvatarSelection selection = model.ApplyEditorSelection(outside);

            Assert.That(selection.Candidate, Is.SameAs(first));
            Assert.That(
                selection.Origin,
                Is.EqualTo(AvatarSelectionOrigin.AutomaticEditorSelection));
        }

        [Test]
        public void EditorSelection_OutsideAvatarsWithoutCurrentChoice_IsUnresolved()
        {
            AvatarDiscoveryCandidate first = CreateCandidate("First");
            AvatarDiscoveryCandidate second = CreateCandidate("Second");
            GameObject outside = CreateGameObject("Outside");
            model.ApplyDiscoveryResult(CreateResult(first, second), null);

            AvatarSelection selection = model.ApplyEditorSelection(outside);

            Assert.That(
                selection.State,
                Is.EqualTo(AvatarSelectionState.Unresolved));
        }

        [Test]
        public void Refresh_InvalidManualSelectionRerunsAutomaticEditorMapping()
        {
            AvatarDiscoveryCandidate first = CreateCandidate("First");
            AvatarDiscoveryCandidate second = CreateCandidate("Second");
            AvatarDiscoveryCandidate third = CreateCandidate("Third");
            model.ApplyDiscoveryResult(CreateResult(first, second, third), null);
            Assert.That(model.TrySelectManual(first), Is.True);
            Invalidate(first);
            AvatarDiscoveryCandidate refreshedSecond = CopyCandidate(second);
            AvatarDiscoveryCandidate refreshedThird = CopyCandidate(third);

            AvatarSelection selection = model.ApplyDiscoveryResult(
                CreateResult(refreshedSecond, refreshedThird),
                third.AvatarRoot);

            Assert.That(selection.Candidate, Is.SameAs(refreshedThird));
            Assert.That(
                selection.Origin,
                Is.EqualTo(AvatarSelectionOrigin.AutomaticEditorSelection));
        }

        [Test]
        public void Refresh_InvalidAutomaticSelectionDoesNotSelectFirstCandidate()
        {
            AvatarDiscoveryCandidate first = CreateCandidate("First");
            AvatarDiscoveryCandidate second = CreateCandidate("Second");
            AvatarDiscoveryCandidate third = CreateCandidate("Third");
            model.ApplyDiscoveryResult(
                CreateResult(first, second, third),
                first.AvatarRoot);
            Invalidate(first);
            AvatarDiscoveryCandidate refreshedSecond = CopyCandidate(second);
            AvatarDiscoveryCandidate refreshedThird = CopyCandidate(third);

            AvatarSelection selection = model.ApplyDiscoveryResult(
                CreateResult(refreshedSecond, refreshedThird),
                null);

            Assert.That(
                selection.State,
                Is.EqualTo(AvatarSelectionState.Unresolved));
            Assert.That(selection.Candidate, Is.Null);
        }

        [Test]
        public void TrySelectManual_RejectsStaleCandidateWithoutChoosingByOrder()
        {
            AvatarDiscoveryCandidate stale = CreateCandidate("Stale");
            AvatarDiscoveryCandidate second = CreateCandidate("Second");
            AvatarDiscoveryCandidate third = CreateCandidate("Third");
            model.ApplyDiscoveryResult(CreateResult(stale, second, third), null);
            Invalidate(stale);

            bool selected = model.TrySelectManual(stale);

            Assert.That(selected, Is.False);
            Assert.That(model.DiscoveryResult.Candidates, Has.Count.EqualTo(2));
            Assert.That(
                model.CurrentSelection.State,
                Is.EqualTo(AvatarSelectionState.Unresolved));
            Assert.That(model.CurrentSelection.Candidate, Is.Null);
        }

        [Test]
        public void ApplyDiscoveryResult_WhenValidityCheckThrows_PreservesState()
        {
            AvatarDiscoveryCandidate stable = CreateCandidate("Stable");
            bool throwOnSecond = false;
            AvatarSelectionModel atomicModel = new AvatarSelectionModel(candidate =>
            {
                if (throwOnSecond && candidate.DisplayName == "Second")
                {
                    throw new InvalidOperationException("Injected failure");
                }

                return true;
            });
            AvatarDiscoveryResult stableResult = CreateResult(stable);
            AvatarSelection stableSelection = atomicModel.ApplyDiscoveryResult(
                stableResult,
                null);
            AvatarDiscoveryResult publishedResult = atomicModel.DiscoveryResult;
            AvatarDiscoveryCandidate second = CreateCandidate("Second");
            throwOnSecond = true;

            Assert.Throws<InvalidOperationException>(() =>
                atomicModel.ApplyDiscoveryResult(
                    CreateResult(stable, second),
                    null));
            Assert.That(atomicModel.DiscoveryResult, Is.SameAs(publishedResult));
            Assert.That(atomicModel.CurrentSelection, Is.SameAs(stableSelection));
        }

        private bool IsCandidateLive(AvatarDiscoveryCandidate candidate)
        {
            if (candidate == null
                || candidate.DescriptorIdentity == null
                || candidate.AvatarRoot == null)
            {
                return false;
            }

            foreach (UnityObject invalidIdentity in invalidIdentities)
            {
                if (ReferenceEquals(
                    invalidIdentity,
                    candidate.DescriptorIdentity))
                {
                    return false;
                }
            }

            return true;
        }

        private void Invalidate(AvatarDiscoveryCandidate candidate)
        {
            invalidIdentities.Add(candidate.DescriptorIdentity);
        }

        private AvatarDiscoveryCandidate CreateCandidate(
            string displayName,
            GameObject avatarRoot = null,
            UnityObject descriptorIdentity = null,
            int componentOrdinal = 0)
        {
            GameObject root = avatarRoot ?? CreateGameObject(displayName);
            UnityObject identity = descriptorIdentity ?? root;
            return new AvatarDiscoveryCandidate(
                identity,
                root,
                componentOrdinal,
                displayName,
                "Assets/Test.unity",
                displayName + " [" + root.transform.GetSiblingIndex() + "]",
                true,
                "Assets/Test.unity",
                0,
                "Test",
                new[] { root.transform.GetSiblingIndex() },
                identity.GetInstanceID(),
                root.scene.handle);
        }

        private static AvatarDiscoveryCandidate CopyCandidate(
            AvatarDiscoveryCandidate candidate)
        {
            int[] siblingIndices = new int[candidate.HierarchyDepth];
            for (int depth = 0; depth < siblingIndices.Length; depth++)
            {
                siblingIndices[depth] = candidate.GetHierarchySiblingIndex(depth);
            }

            return new AvatarDiscoveryCandidate(
                candidate.DescriptorIdentity,
                candidate.AvatarRoot,
                candidate.DescriptorComponentOrdinal,
                candidate.DisplayName,
                candidate.SceneIdentity,
                candidate.HierarchyDisplayPath,
                candidate.IsSavedScene,
                candidate.NormalizedSavedScenePath,
                candidate.LoadedSceneIndex,
                candidate.SceneName,
                siblingIndices,
                candidate.DescriptorInstanceId,
                candidate.SceneHandle);
        }

        private GameObject CreateGameObject(
            string name,
            Transform parent = null)
        {
            GameObject gameObject = new GameObject(name);
            objects.Add(gameObject);
            if (parent != null)
            {
                gameObject.transform.SetParent(parent, false);
            }

            return gameObject;
        }

        private static AvatarDiscoveryResult CreateResult(
            params AvatarDiscoveryCandidate[] candidates)
        {
            return new AvatarDiscoveryResult(candidates);
        }
    }
}
