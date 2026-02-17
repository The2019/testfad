from OCP.gp import gp_Pnt, gp_Vec, gp_Dir, gp_Ax1, gp_Ax2
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace, BRepBuilderAPI_Sewing
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakeSphere
from OCP.BRepFeatures import BRepFeatures_MakeDraft
from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet, BRepFilletAPI_MakeChamfer
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon
from OCP.GCE2d import GCE2d_MakeCircle, GCE2d_MakeLine, GCE2d_MakeArcOfCircle
from OCP.Geom2d import Geom2d_Circle, Geom2d_Line, Geom2d_Arc
from OCP.GCE2dMakeSegment import GCE2d_MakeSegment
from OCP.TopoDS import TopoDS_Wire, TopoDS_Face, TopoDS_Solid
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePrism
from OCP.BRepPrimAPI import BRepPrimAPI_MakeRevolution
from OCP.STEPCAFControl import STEPCAFControl_Writer
from OCP.STEPControl import STEPControl_Writer as STEPWriter
from OCP.STLAPI import STLApi_Writer
from OCP.Quantity import Quantity_Color
import json
import os

class SketchGeometry:
    """Handles 2D sketch geometry creation"""
    
    @staticmethod
    def create_line(p1, p2):
        """Create a line from p1 to p2"""
        pnt1 = gp_Pnt(p1[0], p1[1], 0)
        pnt2 = gp_Pnt(p2[0], p2[1], 0)
        return {
            'type': 'line',
            'p1': p1,
            'p2': p2
        }
    
    @staticmethod
    def create_circle(center, radius):
        """Create a circle"""
        return {
            'type': 'circle',
            'center': center,
            'radius': radius
        }
    
    @staticmethod
    def create_arc(center, radius, start_angle, end_angle):
        """Create an arc"""
        return {
            'type': 'arc',
            'center': center,
            'radius': radius,
            'start_angle': start_angle,
            'end_angle': end_angle
        }
    
    @staticmethod
    def create_rectangle(p1, width, height):
        """Create a rectangle"""
        return {
            'type': 'rectangle',
            'p1': p1,
            'width': width,
            'height': height
        }
    
    @staticmethod
    def build_wire_from_sketch(sketch_geometry):
        """Build an OCP wire from sketch geometry"""
        edges = []
        
        for geom in sketch_geometry:
            if geom['type'] == 'line':
                p1 = gp_Pnt(geom['p1'][0], geom['p1'][1], 0)
                p2 = gp_Pnt(geom['p2'][0], geom['p2'][1], 0)
                edge = BRepBuilderAPI_MakeEdge(p1, p2).Edge()
                edges.append(edge)
            
            elif geom['type'] == 'circle':
                center = gp_Pnt(geom['center'][0], geom['center'][1], 0)
                circle = GCE2d_MakeCircle(gp_Pnt2d(geom['center'][0], geom['center'][1]), geom['radius']).Value()
                # Create 3D circle
                circle_3d = Geom_Circle(gp_Ax2(center, gp_Dir(0, 0, 1)), geom['radius'])
                edge = BRepBuilderAPI_MakeEdge(circle_3d.Handle(), 0, 2 * 3.14159).Edge()
                edges.append(edge)
            
            elif geom['type'] == 'arc':
                center = gp_Pnt(geom['center'][0], geom['center'][1], 0)
                start_angle = geom['start_angle']
                end_angle = geom['end_angle']
                radius = geom['radius']
                
                start_pnt = gp_Pnt(
                    center.X() + radius * __import__('math').cos(start_angle),
                    center.Y() + radius * __import__('math').sin(start_angle),
                    0
                )
                end_pnt = gp_Pnt(
                    center.X() + radius * __import__('math').cos(end_angle),
                    center.Y() + radius * __import__('math').sin(end_angle),
                    0
                )
        
        if edges:
            wire_builder = BRepBuilderAPI_MakeWire()
            for edge in edges:
                wire_builder.Add(edge)
            return wire_builder.Wire()
        
        return None

class Constraints:
    """Handles constraint definitions"""
    
    @staticmethod
    def create_coincident(entity1_id, entity2_id):
        return {'type': 'coincident', 'e1': entity1_id, 'e2': entity2_id}
    
    @staticmethod
    def create_horizontal(entity_id):
        return {'type': 'horizontal', 'entity': entity_id}
    
    @staticmethod
    def create_vertical(entity_id):
        return {'type': 'vertical', 'entity': entity_id}
    
    @staticmethod
    def create_parallel(entity1_id, entity2_id):
        return {'type': 'parallel', 'e1': entity1_id, 'e2': entity2_id}
    
    @staticmethod
    def create_perpendicular(entity1_id, entity2_id):
        return {'type': 'perpendicular', 'e1': entity1_id, 'e2': entity2_id}
    
    @staticmethod
    def create_distance(entity_id, distance):
        return {'type': 'distance', 'entity': entity_id, 'value': distance}
    
    @staticmethod
    def create_radius(circle_id, radius):
        return {'type': 'radius', 'circle': circle_id, 'value': radius}

class Part3D:
    """Handles 3D part operations"""
    
    @staticmethod
    def extrude(wire, depth):
        """Extrude a 2D profile"""
        face = BRepBuilderAPI_MakeFace(wire, True).Face()
        direction = gp_Vec(0, 0, depth)
        prism = BRepBuilderAPI_MakePrism(face, direction).Shape()
        return prism
    
    @staticmethod
    def revolve(wire, axis_origin, axis_direction, angle):
        """Revolve a 2D profile"""
        face = BRepBuilderAPI_MakeFace(wire, True).Face()
        axis = gp_Ax1(gp_Pnt(axis_origin[0], axis_origin[1], axis_origin[2]),
                      gp_Dir(axis_direction[0], axis_direction[1], axis_direction[2]))
        revolve = BRepPrimAPI_MakeRevolution(axis, face, angle).Shape()
        return revolve
    
    @staticmethod
    def fillet(shape, radius, edge_indices=None):
        """Apply fillet operation"""
        try:
            fillet = BRepFilletAPI_MakeFillet(shape)
            
            # Get edges and apply fillet
            from OCP.TopExp import TopExp_Explorer
            from OCP.TopAbs import TopAbs_EDGE
            
            explorer = TopExp_Explorer(shape, TopAbs_EDGE)
            edge_count = 0
            
            while explorer.More():
                edge = explorer.Current()
                
                if edge_indices is None or edge_count in edge_indices:
                    fillet.Add(radius, edge)
                
                explorer.Next()
                edge_count += 1
            
            return fillet.Shape()
        except Exception as e:
            print(f"Fillet error: {e}")
            return shape
    
    @staticmethod
    def chamfer(shape, size, edge_indices=None):
        """Apply chamfer operation"""
        try:
            chamfer = BRepFilletAPI_MakeChamfer(shape)
            
            from OCP.TopExp import TopExp_Explorer
            from OCP.TopAbs import TopAbs_EDGE
            
            explorer = TopExp_Explorer(shape, TopAbs_EDGE)
            edge_count = 0
            
            while explorer.More():
                edge = explorer.Current()
                
                if edge_indices is None or edge_count in edge_indices:
                    chamfer.Add(size, edge)
                
                explorer.Next()
                edge_count += 1
            
            return chamfer.Shape()
        except Exception as e:
            print(f"Chamfer error: {e}")
            return shape

class FileExport:
    """Handles file export operations"""
    
    @staticmethod
    def export_step(shape, filepath):
        """Export shape to STEP format"""
        try:
            writer = STEPWriter()
            writer.Write(shape, filepath)
            return True, f"STEP file exported to {filepath}"
        except Exception as e:
            return False, f"Error exporting STEP: {str(e)}"
    
    @staticmethod
    def export_stl(shape, filepath, deflection=0.1):
        """Export shape to STL format"""
        try:
            writer = STLApi_Writer()
            writer.Write(shape, filepath, deflection)
            return True, f"STL file exported to {filepath}"
        except Exception as e:
            return False, f"Error exporting STL: {str(e)}"