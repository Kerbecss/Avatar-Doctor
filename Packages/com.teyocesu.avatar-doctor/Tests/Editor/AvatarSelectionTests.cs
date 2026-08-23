using System;
using NUnit.Framework;
using Teyocesu.AvatarDoctor.Editor.Discovery;
using Teyocesu.AvatarDoctor.Editor.Selection;
using UnityEngine;

namespace Teyocesu.AvatarDoctor.Editor.Tests
{
    internal sealed class AvatarSelectionTests
    {
        private GameObject identity;

        [SetUp]
        public void SetUp()
        {
            identity = new GameObject("Selection Identity");
        }

        [TearDown]
        public void TearDown()
        {
            if (identity != null)
            {
                UnityEngine.Object.DestroyImmediate(identity);
            }
        }

        [Test]
        public void CreateEmpty_ContainsNoCandidateOrOrigin()
        {
            AvatarSelection selection = AvatarSelection.CreateEmpty();

            Assert.That(selection.State, Is.EqualTo(AvatarSelectionState.Empty));
            Assert.That(selection.Candidate, Is.Null);
            Assert.That(selection.Origin, Is.Null);
        }

        [Test]
        public void CreateUnresolved_ContainsNoCandidateOrOrigin()
        {
            AvatarSelection selection = AvatarSelection.CreateUnresolved();

            Assert.That(
                selection.State,
                Is.EqualTo(AvatarSelectionState.Unresolved));
            Assert.That(selection.Candidate, Is.Null);
            Assert.That(selection.Origin, Is.Null);
        }

        [Test]
        public void CreateSelected_ContainsCandidateAndOrigin()
        {
            AvatarDiscoveryCandidate candidate = CreateCandidate();

            AvatarSelection selection = AvatarSelection.CreateSelected(
                candidate,
                AvatarSelectionOrigin.Manual);

            Assert.That(
                selection.State,
                Is.EqualTo(AvatarSelectionState.Selected));
            Assert.That(selection.Candidate, Is.SameAs(candidate));
            Assert.That(selection.Origin, Is.EqualTo(AvatarSelectionOrigin.Manual));
        }

        [Test]
        public void CreateSelected_WithNullCandidate_Throws()
        {
            Assert.Throws<ArgumentNullException>(() =>
                AvatarSelection.CreateSelected(
                    null,
                    AvatarSelectionOrigin.Manual));
        }

        private AvatarDiscoveryCandidate CreateCandidate()
        {
            return new AvatarDiscoveryCandidate(
                identity,
                identity,
                0,
                identity.name,
                "Assets/Test.unity",
                identity.name + " [0]",
                true,
                "Assets/Test.unity",
                0,
                "Test",
                new[] { 0 },
                identity.GetInstanceID(),
                identity.scene.handle);
        }
    }
}
