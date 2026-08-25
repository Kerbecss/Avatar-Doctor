using System;
using System.Collections.Generic;
using NUnit.Framework;
using Teyocesu.AvatarDoctor.Editor.Discovery;
using Teyocesu.AvatarDoctor.Editor.Selection;
using Teyocesu.AvatarDoctor.Editor.UI;
using UnityEngine;
using UnityObject = UnityEngine.Object;

namespace Teyocesu.AvatarDoctor.Editor.Tests
{
    internal sealed class AvatarDoctorWindowControllerTests
    {
        private readonly List<GameObject> objects = new List<GameObject>();
        private readonly List<string> logMessages = new List<string>();
        private FakeEventSource eventSource;
        private int renderCount;

        [SetUp]
        public void SetUp()
        {
            eventSource = new FakeEventSource();
            renderCount = 0;
            logMessages.Clear();
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
        }

        [Test]
        public void Enable_SchedulesInitialDiscoveryAndCoalescesRefreshEvents()
        {
            int discoverCount = 0;
            AvatarDoctorWindowController controller = CreateController(
                () =>
                {
                    discoverCount++;
                    return CreateResult();
                });

            controller.Enable();
            eventSource.RaiseHierarchyChanged();
            eventSource.RaiseSceneOpened();
            eventSource.RaiseSceneClosed();

            Assert.That(eventSource.ScheduleCount, Is.EqualTo(1));
            Assert.That(controller.IsRefreshPending, Is.True);

            eventSource.ExecutePending();

            Assert.That(discoverCount, Is.EqualTo(1));
            Assert.That(controller.IsRefreshPending, Is.False);
            Assert.That(controller.DiscoveryResult.CountState,
                Is.EqualTo(AvatarDiscoveryState.None));

            eventSource.RaiseHierarchyChanged();
            Assert.That(eventSource.ScheduleCount, Is.EqualTo(2));
            controller.Dispose();
        }

        [Test]
        public void RefreshExplicit_CancelsPendingRefreshAndClearsSuccessfulError()
        {
            bool fail = true;
            int discoverCount = 0;
            AvatarDiscoveryResult result = CreateResult();
            AvatarDoctorWindowController controller = CreateController(
                () =>
                {
                    discoverCount++;
                    if (fail)
                    {
                        throw new InvalidOperationException("Injected discovery failure");
                    }

                    return result;
                });

            controller.Enable();
            controller.RefreshExplicit();

            Assert.That(discoverCount, Is.EqualTo(1));
            Assert.That(eventSource.CancelCount, Is.EqualTo(1));
            Assert.That(controller.TransientOperationalError,
                Does.Contain("Avatar Doctor"));
            Assert.That(logMessages, Has.Count.EqualTo(1));
            Assert.That(logMessages[0], Does.Contain("avatar discovery refresh"));

            fail = false;
            controller.RefreshExplicit();

            Assert.That(discoverCount, Is.EqualTo(2));
            Assert.That(controller.TransientOperationalError, Is.Null);
            Assert.That(controller.DiscoveryResult.CountState,
                Is.EqualTo(AvatarDiscoveryState.None));
            Assert.That(eventSource.ExecutePending(), Is.False);
            controller.Dispose();
        }

        [Test]
        public void OperationalDiscoveryError_PreservesLastStateAndRefreshRecovers()
        {
            bool fail = false;
            AvatarDiscoveryCandidate first = CreateCandidate("First", 0);
            AvatarDiscoveryCandidate second = CreateCandidate("Second", 0);
            int discoverCount = 0;
            AvatarDoctorWindowController controller = CreateController(
                () =>
                {
                    discoverCount++;
                    if (fail)
                    {
                        throw new InvalidOperationException(
                            "Injected discovery failure");
                    }

                    return CreateResult(first, second);
                });

            controller.Enable();
            eventSource.ExecutePending();
            AvatarDiscoveryResult publishedResult = controller.DiscoveryResult;
            AvatarSelection publishedSelection = controller.CurrentSelection;

            fail = true;
            controller.RefreshExplicit();

            Assert.That(discoverCount, Is.EqualTo(2));
            Assert.That(controller.DiscoveryResult, Is.SameAs(publishedResult));
            Assert.That(controller.CurrentSelection, Is.SameAs(publishedSelection));
            Assert.That(
                controller.TransientOperationalError,
                Does.Contain("avatar discovery refresh"));
            Assert.That(logMessages, Has.Count.EqualTo(1));

            fail = false;
            controller.RefreshExplicit();

            Assert.That(discoverCount, Is.EqualTo(3));
            Assert.That(controller.TransientOperationalError, Is.Null);
            Assert.That(
                controller.DiscoveryResult,
                Is.Not.SameAs(publishedResult));
            controller.Dispose();
        }

        [Test]
        public void SelectionChanged_ReevaluatesCurrentResultWithoutRescanning()
        {
            AvatarDiscoveryCandidate first = CreateCandidate("First", 0);
            AvatarDiscoveryCandidate second = CreateCandidate("Second", 0);
            int discoverCount = 0;
            AvatarDoctorWindowController controller = CreateController(
                () =>
                {
                    discoverCount++;
                    return CreateResult(first, second);
                });

            controller.Enable();
            eventSource.ExecutePending();
            eventSource.ActiveEditorSelection = second.AvatarRoot;
            eventSource.RaiseSelectionChanged();

            Assert.That(discoverCount, Is.EqualTo(1));
            Assert.That(
                controller.CurrentSelection.Candidate,
                Is.SameAs(second));
            Assert.That(
                controller.CurrentSelection.Origin,
                Is.EqualTo(AvatarSelectionOrigin.AutomaticEditorSelection));
            controller.Dispose();
        }

        [Test]
        public void ManualSelection_RemainsStickyAcrossEditorSelectionChanges()
        {
            AvatarDiscoveryCandidate first = CreateCandidate("First", 0);
            AvatarDiscoveryCandidate second = CreateCandidate("Second", 1);
            AvatarDoctorWindowController controller = CreateController(
                () => CreateResult(first, second));

            controller.Enable();
            eventSource.ExecutePending();
            Assert.That(controller.TrySelectManual(second), Is.True);
            eventSource.ActiveEditorSelection = first.AvatarRoot;
            eventSource.RaiseSelectionChanged();

            Assert.That(
                controller.CurrentSelection.Candidate,
                Is.SameAs(second));
            Assert.That(
                controller.CurrentSelection.Origin,
                Is.EqualTo(AvatarSelectionOrigin.Manual));
            controller.Dispose();
        }

        [Test]
        public void DisableAndReenable_DoesNotAccumulateCallbacks()
        {
            int discoverCount = 0;
            AvatarDoctorWindowController controller = CreateController(
                () =>
                {
                    discoverCount++;
                    return CreateResult();
                });

            controller.Enable();
            controller.Disable();
            eventSource.RaiseHierarchyChanged();
            Assert.That(eventSource.ScheduleCount, Is.EqualTo(1));
            Assert.That(eventSource.ExecutePending(), Is.False);

            controller.Enable();
            eventSource.RaiseHierarchyChanged();
            eventSource.RaiseHierarchyChanged();
            Assert.That(eventSource.ScheduleCount, Is.EqualTo(2));
            eventSource.ExecutePending();
            Assert.That(discoverCount, Is.EqualTo(1));
            controller.Dispose();
            Assert.That(eventSource.DisposeCount, Is.EqualTo(1));
        }

        [Test]
        public void OperationalSelectionError_PreservesLastConsistentState()
        {
            bool fail = false;
            AvatarSelectionModel model = new AvatarSelectionModel(candidate =>
            {
                if (fail)
                {
                    throw new InvalidOperationException("Injected selection failure");
                }

                return true;
            });
            AvatarDiscoveryCandidate first = CreateCandidate("First", 0);
            AvatarDiscoveryCandidate second = CreateCandidate("Second", 1);
            AvatarDoctorWindowController controller = CreateController(
                () => CreateResult(first, second),
                model);

            controller.Enable();
            eventSource.ExecutePending();
            AvatarDiscoveryResult publishedResult = controller.DiscoveryResult;
            AvatarSelection publishedSelection = controller.CurrentSelection;
            fail = true;
            eventSource.ActiveEditorSelection = first.AvatarRoot;
            eventSource.RaiseSelectionChanged();

            Assert.That(controller.DiscoveryResult, Is.SameAs(publishedResult));
            Assert.That(controller.CurrentSelection, Is.SameAs(publishedSelection));
            Assert.That(controller.TransientOperationalError,
                Does.Contain("Editor selection observation"));
            Assert.That(logMessages, Has.Count.EqualTo(1));
            controller.Dispose();
        }

        [Test]
        public void CandidateLabels_DisambiguateSameRootDescriptorsWithoutInstanceId()
        {
            GameObject root = CreateGameObject("AvatarRoot");
            AvatarDiscoveryCandidate first = CreateCandidate(
                "AvatarRoot",
                0,
                root);
            AvatarDiscoveryCandidate second = CreateCandidate(
                "AvatarRoot",
                1,
                root);

            IReadOnlyList<string> labels = AvatarDoctorWindow.BuildCandidateLabels(
                new[] { first, second });

            Assert.That(labels[0], Does.Contain("Descriptor 1"));
            Assert.That(labels[1], Does.Contain("Descriptor 2"));
            Assert.That(labels[0], Does.Contain(first.SceneIdentity));
            Assert.That(labels[0], Does.Contain(first.HierarchyDisplayPath));
            Assert.That(labels[0], Does.Not.Contain("InstanceID"));
            Assert.That(labels[0], Does.Not.Contain(
                first.DescriptorInstanceId.ToString()));
        }

        [Test]
        public void CandidateLabels_DistinguishDuplicateNamesByHierarchy()
        {
            GameObject firstRoot = CreateGameObject("AvatarRoot");
            GameObject secondRoot = CreateGameObject("AvatarRoot");
            AvatarDiscoveryCandidate first = CreateCandidate(
                "AvatarRoot",
                0,
                firstRoot);
            AvatarDiscoveryCandidate second = CreateCandidate(
                "AvatarRoot",
                0,
                secondRoot);

            IReadOnlyList<string> labels = AvatarDoctorWindow.BuildCandidateLabels(
                new[] { first, second });

            Assert.That(labels[0], Is.Not.EqualTo(labels[1]));
            Assert.That(labels[0], Does.Contain(first.HierarchyDisplayPath));
            Assert.That(labels[1], Does.Contain(second.HierarchyDisplayPath));
            Assert.That(labels[0], Does.Not.Contain("Descriptor"));
            Assert.That(labels[1], Does.Not.Contain("Descriptor"));
        }

        private AvatarDoctorWindowController CreateController(
            Func<AvatarDiscoveryResult> discover,
            AvatarSelectionModel model = null)
        {
            return new AvatarDoctorWindowController(
                eventSource,
                discover,
                model ?? new AvatarSelectionModel(candidate => true),
                () => renderCount++,
                message => logMessages.Add(message));
        }

        private AvatarDiscoveryCandidate CreateCandidate(
            string name,
            int ordinal,
            GameObject root = null)
        {
            GameObject avatarRoot = root ?? CreateGameObject(name);
            GameObject identity = CreateGameObject(name + " Identity");
            return new AvatarDiscoveryCandidate(
                identity,
                avatarRoot,
                ordinal,
                avatarRoot.name,
                "Assets/Test.unity",
                avatarRoot.name + " [" + avatarRoot.transform.GetSiblingIndex() + "]",
                true,
                "Assets/Test.unity",
                0,
                "Test",
                new[] { avatarRoot.transform.GetSiblingIndex() },
                identity.GetInstanceID(),
                avatarRoot.scene.handle);
        }

        private GameObject CreateGameObject(string name)
        {
            GameObject gameObject = new GameObject(name);
            objects.Add(gameObject);
            return gameObject;
        }

        private static AvatarDiscoveryResult CreateResult(
            params AvatarDiscoveryCandidate[] candidates)
        {
            return new AvatarDiscoveryResult(candidates);
        }

        private sealed class FakeEventSource : IAvatarDoctorEditorEventSource
        {
            private Action pendingCallback;

            internal int ScheduleCount { get; private set; }

            internal int CancelCount { get; private set; }

            internal int DisposeCount { get; private set; }

            internal UnityObject ActiveEditorSelection { get; set; }

            public event Action HierarchyChanged;

            public event Action SceneOpened;

            public event Action SceneClosed;

            public event Action SelectionChanged;

            UnityObject IAvatarDoctorEditorEventSource.ActiveEditorSelection =>
                ActiveEditorSelection;

            public void ScheduleDelayCall(Action callback)
            {
                ScheduleCount++;
                pendingCallback = callback;
            }

            public void CancelDelayCall(Action callback)
            {
                CancelCount++;
                pendingCallback = null;
            }

            public void Dispose()
            {
                DisposeCount++;
                pendingCallback = null;
                HierarchyChanged = null;
                SceneOpened = null;
                SceneClosed = null;
                SelectionChanged = null;
            }

            internal void RaiseHierarchyChanged()
            {
                HierarchyChanged?.Invoke();
            }

            internal void RaiseSceneOpened()
            {
                SceneOpened?.Invoke();
            }

            internal void RaiseSceneClosed()
            {
                SceneClosed?.Invoke();
            }

            internal void RaiseSelectionChanged()
            {
                SelectionChanged?.Invoke();
            }

            internal bool ExecutePending()
            {
                Action callback = pendingCallback;
                pendingCallback = null;
                if (callback == null)
                {
                    return false;
                }

                callback();
                return true;
            }
        }
    }
}
