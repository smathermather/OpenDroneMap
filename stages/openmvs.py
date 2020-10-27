import shutil, os, glob, math

from opendm import log
from opendm import io
from opendm import system
from opendm import context
from opendm import point_cloud
from opendm import types
from opendm.osfm import OSFMContext

class ODMOpenMVSStage(types.ODM_Stage):
    def process(self, args, outputs):
        # get inputs
        tree = outputs['tree']
        reconstruction = outputs['reconstruction']
        photos = reconstruction.photos

        if not photos:
            log.ODM_ERROR('Not enough photos in photos array to start OpenMVS')
            exit(1)

        # check if reconstruction was done before
        if not io.file_exists(tree.openmvs_model) or self.rerun():
            if io.dir_exists(tree.openmvs):
                shutil.rmtree(tree.openmvs)

            # export reconstruction from opensfm
            octx = OSFMContext(tree.opensfm)
            cmd = 'export_openmvs'
            if reconstruction.multi_camera:
                # Export only the primary band
                primary = reconstruction.multi_camera[0]
                image_list = os.path.join(tree.opensfm, "image_list_%s.txt" % primary['name'].lower())
                cmd += ' --image_list "%s"' % image_list
            octx.run(cmd)
            
            self.update_progress(10)

            depthmaps_dir = os.path.join(tree.openmvs, "depthmaps")
            if not io.dir_exists(depthmaps_dir):
                os.mkdir(depthmaps_dir)

            resolution_level = int(float(outputs['undist_image_max_size']) / (2*args.depthmap_resolution))

            config = [
                " --resolution-level %s" % resolution_level,
	            "--min-resolution %s" % args.depthmap_resolution,
                "--max-resolution %s" % outputs['undist_image_max_size'],
                "--max-threads %s" % args.max_concurrency,
                '-w "%s"' % depthmaps_dir, 
                "-v 0",
            ]

            log.ODM_INFO("Running dense reconstruction. This might take a while.")
            
            system.run('%s "%s" %s' % (context.omvs_densify_path, 
                                       os.path.join(tree.openmvs, 'scene.mvs'),
                                      ' '.join(config)))

            self.update_progress(90)

            if args.optimize_disk_space:
                dense_scene = os.path.join(tree.openmvs, 'scene_dense.mvs')
                if os.path.exists(dense_scene):
                    os.remove(dense_scene)
                shutil.rmtree(depthmaps_dir)
        else:
            log.ODM_WARNING('Found a valid OpenMVS reconstruction file in: %s' %
                            tree.openmvs_model)